"""Append-only research decisions with evidence, distinct from automatic status."""
from .store import *
def record(run,title,question,observation,interpretation,next_action,**extra):
    row=event(run,'research',title,actor='gpt-6.1-sol',question=question,observation=observation,interpretation=interpretation,next_action=next_action,**extra)
    with lock(Path(run)/'.journal.lock'):
        doc=read(Path(run)/'journal.json',{'entries':[]});doc['entries'].append(row);atomic(Path(run)/'journal.json',doc)
    publish(run)
    return row
