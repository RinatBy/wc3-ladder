"""Evaluate the actual pinned C++ autohost gate, including manual-start mode."""
from pathlib import Path
import re
import sys

source = Path(sys.argv[1]).read_text()
gate = re.search(r'if\( (!m_AutoHostGameName\.empty\( \).*m_LastAutoHostTime >= 30) \)', source)
assert gate, 'Autohost gate not found'
expression = gate[1].replace('!m_AutoHostGameName.empty( )', 'has_name')
expression = expression.replace('GetTime( )', 'now').replace('&&', 'and')
cases = [
    (True, 1, 0, 31, True),   # Room creation works without automatic match start.
    (True, 1, 2, 31, True),   # Existing automatic mode still works.
    (False, 1, 0, 31, False),
    (True, 0, 0, 31, False),
    (True, 1, 0, 29, False),
]
for has_name, maximum, start_players, elapsed, expected in cases:
    values = dict(has_name=has_name, m_AutoHostMaximumGames=maximum,
                  m_AutoHostAutoStartPlayers=start_players, now=elapsed,
                  m_LastAutoHostTime=0)
    actual = bool(eval(expression, {'__builtins__': {}}, values))
    if actual != expected:
        print('MANUAL_AUTOHOST_GATE_FAILED', start_players, elapsed)
        raise SystemExit(42)
print('MANUAL_AUTOHOST_GATE_OK; EXISTING_AUTOMATIC_MODE_OK; DISABLED_AND_INTERVAL_GUARDS_OK')
