"""013 actual shader selection, immutable overlay and private-build CPU contracts."""
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest

import closest_primary as C
import build_closest_primary as B


class PrimaryContracts(unittest.TestCase):
    def test_exact_inverse_for_both_historical_shaders(self):
        for name, pin in C.PINS.items():
            original = (C.SOURCE / name).read_bytes()
            self.assertEqual(C.sha(C.SOURCE / name), pin)
            result = C.overlay(original)
            self.assertNotEqual(result, original)
            self.assertNotIn(b'tolerance', result)
            self.assertIn(C.NEW_BOUND.encode(), result)
            self.assertEqual(C.sha(C.SOURCE / name), pin)

    def test_unregistered_or_drifted_source_is_rejected(self):
        for name in C.PINS:
            with self.assertRaisesRegex(ValueError, 'Unregistered'):
                C.overlay((C.SOURCE / name).read_bytes() + b'\n')

    def test_duplicate_patch_anchor_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'drift'):
            C.once('abcabc', 'abc', 'replacement')

    def test_private_command_moves_only_outputs_and_shader_macros(self):
        command = ['c++', '-DOTHER=1', '-DPHOS_GI_INTEGRATION_SHADER_DIR="old"',
                   '-DPHOS_GI_LANE_A_SHADER_DIR="old"', '-DPHOS_GI_LANE_B_SHADER_DIR="old"',
                   '-I/pinned/include', '-O3', '-DNDEBUG', '-MD', '-MT', 'old.o',
                   '-MF', 'old.d', '-o', 'old.o', '-c', '/pinned/source.cpp']
        entry = {'command': shlex.join(command)}
        result = B.compile_command(entry, Path('/private/new.o'), Path('/private/new.d'), Path('/private/shaders'))
        self.assertEqual(result[-2:], ['-c', '/pinned/source.cpp'])
        self.assertIn('-I/pinned/include', result)
        self.assertIn('-DOTHER=1', result)
        self.assertIn('-O3', result)
        self.assertNotIn('old.o', result)
        self.assertNotIn('old.d', result)
        for macro in ('PHOS_GI_INTEGRATION_SHADER_DIR', 'PHOS_GI_LANE_A_SHADER_DIR', 'PHOS_GI_LANE_B_SHADER_DIR'):
            self.assertIn(f'-D{macro}="/private/shaders"', result)
        self.assertEqual(shlex.split(entry['command']), command)

    def test_malformed_original_command_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unexpected'):
            B.compile_command({'command': 'c++ -c /old.cpp'}, Path('/new.o'), Path('/new.d'), Path('/private'))

    def test_existing_build_and_external_root_are_rejected_before_tools(self):
        with self.assertRaisesRegex(ValueError, 'no overwrite'):
            B.build(C.ROOT / 'out')
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'no overwrite'):
                B.build(Path(tmp) / 'new')

    def test_original_control_manifest_matches_saved_plan_and_all_shader_bytes(self):
        plan, started, shaders = B.original_control_manifest()
        self.assertTrue(plan.is_file())
        self.assertTrue(started.is_file())
        actual = {str(p): C.sha(p) for p in (B.BUILD / 'shaders').glob('*.spv')}
        self.assertEqual(shaders, actual)
        self.assertIn(str(B.BUILD / 'shaders/n001_primary.spv'), shaders)
        self.assertIn(str(B.BUILD / 'shaders/n003_primary_software.spv'), shaders)

    def test_actual_shader_function_float_order_and_legacy_counterexample(self):
        originals = [(C.SOURCE / name).read_bytes() for name in C.PINS]
        functions = [C.selection_function(C.overlay(raw)) for raw in originals]
        self.assertEqual(functions[0], functions[1])
        old = C.selection_function(originals[0]).replace('prefer_hit(', 'legacy_prefer_hit(')
        code = '''#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <limits>
#include <utility>
using uint = unsigned;
using std::max; using std::abs;
const float HIT_ABS_TOL=2e-4f, HIT_REL_TOL=2e-5f;
''' + old + '\n' + functions[0] + '''
int main() {
  unsigned permutations=0;
  const float one=1.0f, up=std::nextafter(one,2.0f), down=std::nextafter(one,0.0f);
  std::array<std::array<std::pair<float,uint>,4>,4> groups{{
    {{{1200.0f,49893},{1199.98f,51389},{1400.0f,1},{1199.98f,60000}}},
    {{{one,100},{up,1},{down,999},{up,0}}},
    {{{one,7},{one,3},{one,99},{one,4}}},
    {{{480.66f,172940},{480.656f,172941},{500.0f,0},{480.656f,200000}}}
  }};
  for (const auto& group:groups) {
    auto expected=*std::min_element(group.begin(),group.end());
    std::array<int,4> order{0,1,2,3};
    do {
      bool found=false; float best=2000; uint id=~0u;
      for(auto at:order) {
        const auto [t,prim]=group[at];
        if(prefer_hit(t,prim,best,id,found)) {best=t;id=prim;found=true;}
      }
      if(!found || best!=expected.first || id!=expected.second) return 1;
      ++permutations;
    } while(std::next_permutation(order.begin(),order.end()));
  }
  if(!legacy_prefer_hit(1200.0f,49893,1199.98f,51389,true)) return 2;
  if(legacy_prefer_hit(1199.98f,51389,1200.0f,49893,true)) return 3;
  if(prefer_hit(1200.0f,49893,1199.98f,51389,true)) return 4;
  if(!prefer_hit(1199.98f,51389,1200.0f,49893,true)) return 5;
  if(permutations!=96) return 6;
  std::cout << "96 exact-float candidate permutations and legacy counterexample PASS\\n";
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'selection.cpp'
            binary = Path(tmp) / 'selection'
            source.write_text(code)
            compile_result = subprocess.run(['c++', '-std=c++20', '-O2', '-fno-fast-math', '-ffp-contract=off',
                                             str(source), '-o', str(binary)], capture_output=True, text=True)
            self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
            p = subprocess.run([str(binary)], capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn('96 exact-float candidate permutations', p.stdout)


if __name__ == '__main__':
    unittest.main()
