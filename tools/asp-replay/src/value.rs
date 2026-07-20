use serde_json::{Map, Value};
use specification_core::Specification;

use crate::specifications::{ClosedObject, MemberType, TimestampShape};

pub(crate) fn member<'a>(value: &'a Value, name: &str) -> Option<&'a Value> {
    value.as_object()?.get(name)
}

pub(crate) fn string<'a>(value: &'a Value, name: &str) -> Option<&'a str> {
    MemberType::string(name)
        .is_satisfied_by(value)
        .then(|| member(value, name).and_then(Value::as_str))
        .flatten()
}

pub(crate) fn uint(value: &Value, name: &str) -> Option<u64> {
    MemberType::unsigned_integer(name)
        .is_satisfied_by(value)
        .then(|| member(value, name).and_then(Value::as_u64))
        .flatten()
}

pub(crate) fn has_only(object: &Map<String, Value>, members: &[&str]) -> bool {
    ClosedObject::new(members).is_satisfied_by(object)
}

pub(crate) fn timestamp_shape(value: &str) -> bool {
    TimestampShape.is_satisfied_by(value)
}

pub(crate) fn timestamp_order_key(value: &str) -> Option<(String, String)> {
    if !timestamp_shape(value) {
        return None;
    }
    let value = value.strip_suffix('Z')?;
    let (seconds, fraction) = value.split_once('.').unwrap_or((value, ""));
    debug_assert_eq!(seconds.len(), 19);
    debug_assert!(fraction.len() <= 9);
    let mut normalized_fraction = fraction.to_owned();
    normalized_fraction.extend(std::iter::repeat_n('0', 9 - fraction.len()));
    Some((seconds.to_owned(), normalized_fraction))
}

pub(crate) fn timestamp_not_after(left: &str, right: &str) -> bool {
    timestamp_order_key(left)
        .zip(timestamp_order_key(right))
        .is_some_and(|(left, right)| left <= right)
}

pub(crate) fn timestamp_epoch_nanos(value: &str) -> Option<i128> {
    if !timestamp_shape(value) {
        return None;
    }
    let number = |start: usize, end: usize| value.get(start..end)?.parse::<i128>().ok();
    let year = number(0, 4)?;
    let month = number(5, 7)?;
    let day = number(8, 10)?;
    let hour = number(11, 13)?;
    let minute = number(14, 16)?;
    let second = number(17, 19)?;
    let leap = year % 4 == 0 && (year % 100 != 0 || year % 400 == 0);
    let month_offsets = [0_i128, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334];
    let days_before_year = year * 365 + (year + 3) / 4 - (year + 99) / 100 + (year + 399) / 400;
    let days_before_month =
        *month_offsets.get((month - 1) as usize)? + if leap && month > 2 { 1 } else { 0 };
    let days = days_before_year + days_before_month + day - 1;
    let fraction = value
        .strip_suffix('Z')?
        .split_once('.')
        .map(|(_, fraction)| fraction)
        .unwrap_or("");
    let mut nanos = fraction.to_owned();
    nanos.extend(std::iter::repeat_n('0', 9 - nanos.len()));
    let nanos = nanos.parse::<i128>().ok()?;
    Some((((days * 24 + hour) * 60 + minute) * 60 + second) * 1_000_000_000 + nanos)
}

pub(crate) fn timestamp_within_seconds(start: &str, end: &str, max_seconds: u64) -> bool {
    timestamp_epoch_nanos(start)
        .zip(timestamp_epoch_nanos(end))
        .is_some_and(|(start, end)| {
            end > start && end - start <= i128::from(max_seconds).saturating_mul(1_000_000_000)
        })
}

pub(crate) fn timestamp_elapsed_within(start: &str, end: &str, max_seconds: u64) -> bool {
    timestamp_epoch_nanos(start)
        .zip(timestamp_epoch_nanos(end))
        .is_some_and(|(start, end)| {
            end >= start && end - start <= i128::from(max_seconds).saturating_mul(1_000_000_000)
        })
}
