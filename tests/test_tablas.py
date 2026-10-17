from sqlalchemy import inspect
from app.database import engine


def test_las_tablas_existen():
    tablas = inspect(engine).get_table_names()
    assert len(tablas) > 0
    print(tablas)