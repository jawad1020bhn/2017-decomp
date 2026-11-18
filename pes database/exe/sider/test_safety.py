"""Shared-memory and failed-install regressions for the eight Master League modules.

    python test_safety.py <PES2017.exe>

Uses the same LuaJIT/Unicorn harness as test_money.py. No Windows/game files are changed.
"""
import gc
from pathlib import Path
import random
import sys

import test_money as tm

HERE = Path(__file__).resolve().parent
NAMES = ('MLCheck', 'MLMoney', 'MLYear', 'MLTransfers', 'MLSimMatch',
         'MLTeamSpirit', 'MLSimToDate', 'MLGrowth')


def installed(name, lines):
    results = tm.results(lines)
    assert len(results) == 1, (name, results)
    expected = 'RESULT: 6 of 6 as expected.' if name == 'MLCheck' else 'RESULT: installed'
    assert results[0].startswith(expected), (name, results)


def main(exe):
    sources = {name: (HERE / (name + '.lua')).read_text(encoding='utf-8') for name in NAMES}
    pristine, game = tm.Game(exe), tm.Game(exe)
    originals, module_writes = {}, {}

    def restore():
        for (address, _), data in originals.items():
            tm.poke(game, address, data)

    orders = [list(NAMES), ['MLCheck', 'MLGrowth', 'MLMoney', 'MLYear', 'MLTransfers',
                           'MLTeamSpirit', 'MLSimToDate', 'MLSimMatch']]
    rng = random.Random(2017)
    dependencies = {'MLMoney': ('MLCheck',), 'MLTransfers': ('MLMoney',)}
    for _ in range(20):
        order, remaining = [], list(NAMES)
        while remaining:
            ready = [name for name in remaining if all(p in order for p in dependencies.get(name, ()))]
            chosen = rng.choice(ready)
            order.append(chosen)
            remaining.remove(chosen)
        orders.append(order)

    for order in orders:
        restore()
        snapshots = []
        for name in order:
            lines, _, writes = tm.run(game, sources[name])
            installed(name, lines)
            module_writes[name] = writes
            for address, count in writes:
                key = address, count
                if key not in originals:
                    originals[key] = pristine.read(address, count)
                for owner, start, data in snapshots:
                    if owner != name:
                        assert address + count <= start or start + len(data) <= address, (
                            name, owner, hex(address), hex(start))
                snapshots.append((name, address, game.read(address, count)))
        for name, address, data in snapshots:
            assert game.read(address, len(data)) == data, (order, name, hex(address))
        gc.collect()
    print('ok 1: all eight modules install in both Growth/SimMatch orders and 20 sampled '
          'orders; no cross-module writes overlap and every installed byte survives')

    # shortcut: current patches are <=32 bytes and caves are larger; use explicit ranges if that changes.
    # SimToDate already tests its READY gate/rollback in test_simdate*.py.
    checked = 0
    for name in ('MLMoney', 'MLTransfers', 'MLYear', 'MLSimMatch', 'MLGrowth', 'MLTeamSpirit'):
        patches = [(a, n) for a, n in module_writes[name] if n <= 32]
        assert patches, name

        def prepare():
            restore()
            if name == 'MLTransfers':
                lines, _, _ = tm.run(game, sources['MLMoney'])
                installed('MLMoney', lines)

        prepare()
        lines, _, _ = tm.run(game, sources[name])
        installed(name, lines)
        patched = {a: game.read(a, n) for a, n in patches}
        for failure, count in patches:
            for partial in (False, True):
                prepare()
                failed = [False]

                def sticky(address):
                    if address != failure:
                        return True
                    if not partial:
                        return False
                    if failed[0]:
                        return True  # the one-time damaged write can be restored
                    failed[0] = True
                    data = patched[address]
                    tm.poke(game, address, data[:-1] + bytes([data[-1] ^ 0x80]))
                    return False

                lines, _, writes = tm.run(game, sources[name], sticky=sticky)
                assert lines[-1].startswith(('RESULT: a change did not go in.',
                                             'RESULT: the change did not go in.')), (name, lines[-1])
                assert 'restored.' in lines[-1], (name, lines[-1])
                for address, size in patches:
                    assert game.read(address, size) == originals[address, size], (
                        name, hex(failure), partial, hex(address), writes)
                if name == 'MLMoney':
                    dependent, _, dependent_writes = tm.run(game, sources['MLTransfers'])
                    assert not dependent_writes and not tm.results(dependent)[0].startswith('RESULT: installed'), (
                        hex(failure), partial, tm.results(dependent))
                checked += 1
        # A host that also refuses restoration must not be logged as recovered.
        prepare()
        failure, count = patches[-1]

        def broken_restore(address):
            if address != failure:
                return True
            data = patched[address]
            tm.poke(game, address, data[:-1] + bytes([data[-1] ^ 0x80]))
            return False

        lines, _, _ = tm.run(game, sources[name], sticky=broken_restore)
        assert 'restore failed.' in lines[-1], (name, lines[-1])
        gc.collect()
    print('ok 2: %d refused/damaged patch writes restore every original patch; refused '
          'restoration is reported for all six patchers' % checked)
    print('all ok')


if __name__ == '__main__':
    main(sys.argv[1])
