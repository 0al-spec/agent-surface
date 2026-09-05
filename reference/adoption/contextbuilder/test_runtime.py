import unittest

from runtime import canonical, loads, object_hash, validate


class RuntimePrimitiveTests(unittest.TestCase):
    def test_normative_hash_vectors(self):
        self.assertEqual(object_hash("grant", {"grant_id": "grant_123", "scopes": ["read"]}),
                         "sha-256:Xbq37_fP9PBiWI3Bv7Ch0t8TV5ikJGm55MxncSeA38Y")
        self.assertEqual(object_hash("manifest", {"a": "x", "z": 1, "surface_hash": "omitted"}),
                         "sha-256:Mckhl9gi8ePkXnuOJtPFNE1pe9LhilOGu1OgzxsXb8A")
        self.assertEqual(canonical({"\ue000": 1, "😀": 2}), '{"😀":2,"\ue000":1}'.encode())

    def test_invalid_json_is_not_repaired(self):
        for raw in ('{"a":1,"a":2}', '-0', '1e400', 'NaN', '1.5', '"\\ud800"', '"\\uffff"', '9007199254740992'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                loads(raw)

    def test_bounded_schema_checks_reject_unknown_shape(self):
        schema = {"type": "object", "additionalProperties": False, "required": ["value"],
                  "properties": {"value": {"type": "string", "maxLength": 3}}}
        validate(schema, {"value": "yes"})
        for value in ({}, {"value": "long"}, {"value": 1}, {"value": "yes", "commit": True}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate(schema, value)
        with self.assertRaises(ValueError):
            validate({"$ref": "https://other.invalid/schema"}, {})
