import os
from pattern.db import Database, pk, field, STRING


def get_database(db_name, clean=False):
    if clean:
        if os.path.exists(db_name):
            os.remove(db_name)
        if os.path.exists(db_name + '-journal'):
            os.remove(db_name + '-journal')
    db = Database(db_name)
    if 'room' not in db.tables:
        db.create('room', fields=[
            pk(),
            field('type', STRING(10)),
            field('email', STRING(100)),
            field('contact_name', STRING(100)),
            field('link', STRING(200)),
            field('rent', STRING(50)),
            field('available', STRING(100)),
        ])
    return db