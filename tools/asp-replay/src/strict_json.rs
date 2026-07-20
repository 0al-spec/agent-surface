use std::fmt;

use serde::Deserialize;
use serde::de::{self, Deserializer, MapAccess, SeqAccess, Visitor};
use serde_json::{Map, Value};

use crate::{MAX_INPUT_BYTES, ReplayError};

const SAFE_INTEGER: i128 = (1_i128 << 53) - 1;

#[derive(Clone, Debug)]
struct StrictValue(Value);

struct StrictVisitor;

fn reject_unicode_noncharacters<E: de::Error>(value: &str) -> Result<(), E> {
    if let Some(code_point) = value.chars().map(u32::from).find(|code_point| {
        (0xfdd0..=0xfdef).contains(code_point)
            || code_point & 0xffff == 0xfffe
            || code_point & 0xffff == 0xffff
    }) {
        return Err(E::custom(format!(
            "Unicode noncharacter U+{code_point:04X} is forbidden"
        )));
    }
    Ok(())
}

impl<'de> Visitor<'de> for StrictVisitor {
    type Value = StrictValue;

    fn expecting(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("duplicate-free I-JSON")
    }

    fn visit_bool<E>(self, value: bool) -> Result<Self::Value, E> {
        Ok(StrictValue(Value::Bool(value)))
    }

    fn visit_i64<E>(self, value: i64) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        if i128::from(value).abs() > SAFE_INTEGER {
            return Err(E::custom("integer is outside the I-JSON safe range"));
        }
        Ok(StrictValue(Value::Number(value.into())))
    }

    fn visit_u64<E>(self, value: u64) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        if i128::from(value) > SAFE_INTEGER {
            return Err(E::custom("integer is outside the I-JSON safe range"));
        }
        Ok(StrictValue(Value::Number(value.into())))
    }

    fn visit_f64<E>(self, value: f64) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        if !value.is_finite() {
            return Err(E::custom("non-finite numbers are forbidden"));
        }
        if value == 0.0 && value.is_sign_negative() {
            return Err(E::custom("JSON negative zero is forbidden"));
        }
        if value.fract() == 0.0 && value.abs() > SAFE_INTEGER as f64 {
            return Err(E::custom(
                "integral number is outside the I-JSON safe range",
            ));
        }
        let number = serde_json::Number::from_f64(value)
            .ok_or_else(|| E::custom("number cannot be represented as binary64"))?;
        Ok(StrictValue(Value::Number(number)))
    }

    fn visit_str<E>(self, value: &str) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        reject_unicode_noncharacters::<E>(value)?;
        Ok(StrictValue(Value::String(value.to_owned())))
    }

    fn visit_string<E>(self, value: String) -> Result<Self::Value, E>
    where
        E: de::Error,
    {
        reject_unicode_noncharacters::<E>(&value)?;
        Ok(StrictValue(Value::String(value)))
    }

    fn visit_none<E>(self) -> Result<Self::Value, E> {
        Ok(StrictValue(Value::Null))
    }

    fn visit_unit<E>(self) -> Result<Self::Value, E> {
        Ok(StrictValue(Value::Null))
    }

    fn visit_some<D>(self, deserializer: D) -> Result<Self::Value, D::Error>
    where
        D: Deserializer<'de>,
    {
        deserializer.deserialize_any(StrictVisitor)
    }

    fn visit_seq<A>(self, mut sequence: A) -> Result<Self::Value, A::Error>
    where
        A: SeqAccess<'de>,
    {
        let mut values = Vec::new();
        while let Some(value) = sequence.next_element::<StrictValue>()? {
            values.push(value.0);
        }
        Ok(StrictValue(Value::Array(values)))
    }

    fn visit_map<A>(self, mut object: A) -> Result<Self::Value, A::Error>
    where
        A: MapAccess<'de>,
    {
        let mut values = Map::new();
        while let Some(key) = object.next_key::<String>()? {
            reject_unicode_noncharacters::<A::Error>(&key)?;
            if values.contains_key(&key) {
                return Err(de::Error::custom(format!(
                    "duplicate JSON object member {key:?}"
                )));
            }
            let value = object.next_value::<StrictValue>()?;
            values.insert(key, value.0);
        }
        Ok(StrictValue(Value::Object(values)))
    }
}

impl<'de> Deserialize<'de> for StrictValue {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        deserializer.deserialize_any(StrictVisitor)
    }
}

fn reject_lexical_negative_zero(document: &str) -> Result<(), ReplayError> {
    let bytes = document.as_bytes();
    let mut index = 0;
    let mut in_string = false;
    let mut escaped = false;
    while index < bytes.len() {
        let byte = bytes[index];
        if in_string {
            if escaped {
                escaped = false;
            } else if byte == b'\\' {
                escaped = true;
            } else if byte == b'"' {
                in_string = false;
            }
            index += 1;
            continue;
        }
        if byte == b'"' {
            in_string = true;
            index += 1;
            continue;
        }
        let boundary = index == 0
            || matches!(
                bytes[index - 1],
                b' ' | b'\t' | b'\r' | b'\n' | b'[' | b'{' | b',' | b':'
            );
        if byte != b'-' || !boundary || bytes.get(index + 1) != Some(&b'0') {
            index += 1;
            continue;
        }
        let start = index;
        index += 2;
        while bytes.get(index).is_some_and(|byte| {
            byte.is_ascii_digit() || matches!(*byte, b'.' | b'e' | b'E' | b'+' | b'-')
        }) {
            index += 1;
        }
        let token = &document[start..index];
        let mantissa = token[1..]
            .split_once(['e', 'E'])
            .map_or(&token[1..], |(mantissa, _)| mantissa);
        if mantissa
            .bytes()
            .filter(|byte| *byte != b'.')
            .all(|byte| byte == b'0')
        {
            return Err(ReplayError::StrictJson(
                "JSON negative zero is forbidden".to_owned(),
            ));
        }
    }
    Ok(())
}

pub(crate) fn parse_strict(document: &[u8]) -> Result<Value, ReplayError> {
    if document.len() > MAX_INPUT_BYTES {
        return Err(ReplayError::StrictJson(format!(
            "input exceeds {MAX_INPUT_BYTES} bytes"
        )));
    }
    let text = std::str::from_utf8(document)
        .map_err(|error| ReplayError::StrictJson(format!("input is not UTF-8: {error}")))?;
    reject_lexical_negative_zero(text)?;
    let mut deserializer = serde_json::Deserializer::from_str(text);
    let value = StrictValue::deserialize(&mut deserializer)
        .map_err(|error| ReplayError::StrictJson(error.to_string()))?
        .0;
    deserializer
        .end()
        .map_err(|error| ReplayError::StrictJson(error.to_string()))?;
    if !value.is_object() {
        return Err(ReplayError::StrictJson(
            "bundle root must be an object".to_owned(),
        ));
    }
    Ok(value)
}
