use base64::Engine;
use base64::engine::general_purpose::URL_SAFE_NO_PAD;
use serde_json::{Map, Value};
use specification_core::Specification;

const DIGEST_PATTERN_LENGTH: usize = 51;

pub(crate) struct CanonicalDigest;

impl Specification<str> for CanonicalDigest {
    fn is_satisfied_by(&self, candidate: &str) -> bool {
        if candidate.len() != DIGEST_PATTERN_LENGTH || !candidate.starts_with("sha-256:") {
            return false;
        }
        URL_SAFE_NO_PAD
            .decode(&candidate[8..])
            .is_ok_and(|bytes| bytes.len() == 32 && URL_SAFE_NO_PAD.encode(bytes) == candidate[8..])
    }
}

pub(crate) struct BundleId;

impl Specification<str> for BundleId {
    fn is_satisfied_by(&self, candidate: &str) -> bool {
        if candidate.is_empty() || candidate.len() > 256 || !candidate.is_ascii() {
            return false;
        }
        let mut bytes = candidate.bytes();
        bytes
            .next()
            .is_some_and(|byte| byte.is_ascii_alphanumeric())
            && bytes.all(|byte| {
                byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b':' | b'-')
            })
    }
}

pub(crate) struct TimestampShape;

impl Specification<str> for TimestampShape {
    fn is_satisfied_by(&self, candidate: &str) -> bool {
        let bytes = candidate.as_bytes();
        if !(candidate.len() == 20 || (22..=30).contains(&candidate.len()))
            || bytes.last() != Some(&b'Z')
            || bytes.get(4) != Some(&b'-')
            || bytes.get(7) != Some(&b'-')
            || bytes.get(10) != Some(&b'T')
            || bytes.get(13) != Some(&b':')
            || bytes.get(16) != Some(&b':')
            || (candidate.len() > 20 && bytes.get(19) != Some(&b'.'))
            || bytes.iter().enumerate().any(|(index, byte)| {
                !matches!(index, 4 | 7 | 10 | 13 | 16 | 19)
                    && index + 1 != candidate.len()
                    && !byte.is_ascii_digit()
            })
        {
            return false;
        }
        let number = |start: usize, end: usize| {
            candidate
                .get(start..end)
                .and_then(|part| part.parse::<u32>().ok())
        };
        let (Some(year), Some(month), Some(day), Some(hour), Some(minute), Some(second)) = (
            number(0, 4),
            number(5, 7),
            number(8, 10),
            number(11, 13),
            number(14, 16),
            number(17, 19),
        ) else {
            return false;
        };
        let leap =
            year.is_multiple_of(4) && (!year.is_multiple_of(100) || year.is_multiple_of(400));
        let days = match month {
            1 | 3 | 5 | 7 | 8 | 10 | 12 => 31,
            4 | 6 | 9 | 11 => 30,
            2 if leap => 29,
            2 => 28,
            _ => return false,
        };
        day >= 1 && day <= days && hour <= 23 && minute <= 59 && second <= 59
    }
}

pub(crate) struct RequiredMembers<'a> {
    names: &'a [&'a str],
}

impl<'a> RequiredMembers<'a> {
    pub(crate) fn new(names: &'a [&'a str]) -> Self {
        Self { names }
    }
}

impl Specification<Value> for RequiredMembers<'_> {
    fn is_satisfied_by(&self, candidate: &Value) -> bool {
        candidate
            .as_object()
            .is_some_and(|object| self.names.iter().all(|name| object.contains_key(*name)))
    }
}

#[derive(Clone, Copy)]
enum JsonMemberKind {
    String,
    UnsignedInteger,
}

pub(crate) struct MemberType<'a> {
    name: &'a str,
    kind: JsonMemberKind,
}

impl<'a> MemberType<'a> {
    pub(crate) fn string(name: &'a str) -> Self {
        Self {
            name,
            kind: JsonMemberKind::String,
        }
    }

    pub(crate) fn unsigned_integer(name: &'a str) -> Self {
        Self {
            name,
            kind: JsonMemberKind::UnsignedInteger,
        }
    }
}

impl Specification<Value> for MemberType<'_> {
    fn is_satisfied_by(&self, candidate: &Value) -> bool {
        let Some(value) = candidate
            .as_object()
            .and_then(|object| object.get(self.name))
        else {
            return false;
        };
        match self.kind {
            JsonMemberKind::String => value.is_string(),
            JsonMemberKind::UnsignedInteger => value.as_u64().is_some(),
        }
    }
}

pub(crate) struct ClosedObject<'a> {
    members: &'a [&'a str],
}

impl<'a> ClosedObject<'a> {
    pub(crate) fn new(members: &'a [&'a str]) -> Self {
        Self { members }
    }
}

impl Specification<Map<String, Value>> for ClosedObject<'_> {
    fn is_satisfied_by(&self, candidate: &Map<String, Value>) -> bool {
        candidate
            .keys()
            .all(|key| self.members.contains(&key.as_str()))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn scalar_specs_preserve_canonical_boundaries() {
        assert!(
            CanonicalDigest.is_satisfied_by("sha-256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
        );
        assert!(
            !CanonicalDigest.is_satisfied_by("sha-256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAB")
        );
        assert!(BundleId.is_satisfied_by("bundle.example:2026_07-20"));
        assert!(!BundleId.is_satisfied_by(""));
        assert!(TimestampShape.is_satisfied_by("2024-02-29T23:59:59.123456789Z"));
        assert!(!TimestampShape.is_satisfied_by("2026-02-29T23:59:59Z"));
    }

    #[test]
    fn object_specs_preserve_presence_type_and_closed_shape() {
        let value = serde_json::json!({"id": "event_1", "attempt": 1});
        assert!(RequiredMembers::new(&["id", "attempt"]).is_satisfied_by(&value));
        assert!(MemberType::string("id").is_satisfied_by(&value));
        assert!(MemberType::unsigned_integer("attempt").is_satisfied_by(&value));
        assert!(
            ClosedObject::new(&["id", "attempt"])
                .is_satisfied_by(value.as_object().expect("fixture is an object"))
        );
        assert!(
            !ClosedObject::new(&["id"])
                .is_satisfied_by(value.as_object().expect("fixture is an object"))
        );
    }
}
