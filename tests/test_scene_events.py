import unittest

from scummbucket.scene_events import SceneEventError, serialize_scene_events


def manifest(*events, clock=None):
    return dict(schema="p4-scene-events/1", clock=clock, events=list(events), source=dict(
        game_edition="synthetic", archive_sha256="a" * 64, logical_room=130, physical_room=72))


def event(kind, evidence="synthetic", tick=None, **payload):
    return dict(kind=kind, evidence=evidence, tick=tick, payload=payload)


class SceneEventTests(unittest.TestCase):
    def test_canonical_bytes_preserve_event_order_and_unknown_branch(self):
        first = event("object_draw", object_id=364, state=1)
        second = event("conditional_transition", condition="Bit92", taken=None)
        second["script"] = dict(kind="ENCD", storage_room=35, id=None, pc=127)
        data = manifest(first, second)
        encoded = serialize_scene_events(data)
        self.assertEqual(encoded, serialize_scene_events(dict(reversed(list(data.items())))))
        self.assertLess(encoded.index(b"object_draw"), encoded.index(b"conditional_transition"))
        self.assertIn(b'"taken":null', encoded)
        self.assertIn(b'"pc":127', encoded)

    def test_invalid_evidence_palette_range_and_boolean_id(self):
        cases = [
            (event("object_draw", evidence="verified", object_id=364, state=1), "evidence"),
            (event("palette_cycle", cycle_id=1, first=180, last=179, flags=0), "palette range"),
            (event("object_draw", object_id=True, state=1), "object_id"),
            (event("unsupported", reason="unhandled opcode"), "unsupported evidence"),
        ]
        for row, message in cases:
            with self.subTest(row=row), self.assertRaisesRegex(SceneEventError, message):
                serialize_scene_events(manifest(row))

    def test_clock_validation_and_equal_ticks(self):
        first = event("script_yield", tick=3)
        second = event("script_stop", tick=3)
        serialize_scene_events(manifest(first, second, clock="timer_units"))
        for data in (manifest(first), manifest(first, dict(second, tick=2), clock="timer_units")):
            with self.assertRaisesRegex(SceneEventError, r"events\[\d+\]\.tick"):
                serialize_scene_events(data)
