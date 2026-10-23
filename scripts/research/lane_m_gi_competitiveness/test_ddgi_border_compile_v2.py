import json
import unittest
from pathlib import Path

import compile_ddgi_border_v2 as V


class RelocatedSdkCompiler(unittest.TestCase):
    def test_six_original_commands_keep_all_flags_and_restore_source_includes(self):
        old = json.loads((V.S.RESULTS / '038-ddgi-shader-compilation.json').read_text())
        rows = [r for r in old['rows'] if r['name'].startswith('blend-')]
        self.assertEqual(len(rows), 6)
        for row in rows:
            original = list(row['command'])
            generated, target = Path('/tmp/relocated.hlsl'), Path('/tmp/relocated.spv')
            cmd = V.interior_command(original, generated, target)
            self.assertEqual(cmd[-2:], ['-I', str(V.S.SDK / 'rtxgi-sdk/shaders/ddgi')])
            restored = cmd[:-2]
            restored[1] = original[1]
            restored[restored.index('-Fo') + 1] = original[original.index('-Fo') + 1]
            self.assertEqual(restored, original)
            self.assertEqual(row['command'], original)
            # The include that caused v1's real CPU failure is now reachable.
            self.assertTrue((Path(cmd[-1]) / 'include/validation/ProbeBlendingDefines.hlsl').is_file())


if __name__ == '__main__':
    unittest.main()
