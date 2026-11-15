"""Export/verify private source packages; never equate integrity with fidelity."""
import argparse
import json
from pathlib import Path
from scummbucket.scene_package import export_source,verify_source

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('operation',choices=['export','verify'])
    p.add_argument('destination',type=Path)
    p.add_argument('--game',type=Path)
    p.add_argument('--room',type=int)
    a=p.parse_args()
    if a.operation=='export':
        if a.game is None or a.room is None:p.error('Export needs --game and --room')
        export_source(a.game,a.room,a.destination)
    print(json.dumps(verify_source(a.destination),indent=2))
