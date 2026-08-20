from sqlalchemy import create_engine

from app.core.diagnostics import check_database


def test_check_database_ok_when_tables_exist(tmp_path):
    db_path = tmp_path / "good.db"
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")

    # init_db (внутри check_database) создаст таблицы на этом движке
    result = check_database(bind_engine=engine)

    assert result.status == "OK"


# TODO: тест на FAIL-случай (БД есть, таблиц нет) — доделать вместе с
# %APPDATA%-слоем. Сейчас check_database сама зовёт init_db и всегда
# создаёт таблицы, поэтому честный FAIL-сценарий появится, когда
# проверка перестанет чинить БД и начнёт только проверять её.