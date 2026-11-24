import click
from tabulate import tabulate

from core.database import connect_to_db
from core.config import load_config
from core.utils import levenshtein
from core.validators import (
    validate_fname,
    validate_lname,
    validate_id,
    validate_customer_find_query,
)


@click.group("customers")
def customers_group():
    pass


@customers_group.command()
@click.option(
    "-fn",
    "--first-name",
    type=str,
    callback=validate_fname,
    required=True,
)
@click.option(
    "-ln",
    "--last-name",
    type=str,
    callback=validate_lname,
    required=True,
)
def add(first_name: str, last_name: str):
    with connect_to_db(load_config()) as db:
        cur = db.cursor()
        result = cur.execute(
            """
            INSERT OR IGNORE INTO customers (first_name, last_name)
            VALUES (?, ?)
            RETURNING id, first_name, last_name, created_at
            """,
            (
                first_name,
                last_name,
            ),
        )
        row = cur.fetchall()
        if result.rowcount > 0:
            click.echo("Запись добавлена")
            click.echo(
                tabulate(
                    row,
                    ["id", "first_name", "last_name", "created_at"],
                )
            )
        else:
            click.echo("Запись уже существует")
        db.commit()
        cur.close()


@customers_group.command()
@click.argument("id", type=int, callback=validate_id, required=True)
def get(id: int):
    with connect_to_db(load_config()) as db:
        cur = db.cursor()
        cur.execute(
            """
            SELECT
                id,
                first_name,
                last_name,
                created_at,
                is_deleted
            FROM customers
            WHERE id = ?
            """,
            (id,),
        )
        if row := cur.fetchall():
            click.echo(f"Найдено {len(row)} записей")
            click.echo(
                tabulate(
                    row, ["id", "first_name", "last_name", "created_at", "is_deleted"]
                )
            )
        else:
            click.echo("Запись не найдена")

        db.commit()
        cur.close()


@customers_group.command()
@click.option("-i", "--id", type=int, callback=validate_id, required=True)
@click.option(
    "-fn",
    "--first-name",
    type=str,
    callback=validate_fname,
    required=True,
)
@click.option(
    "-ln",
    "--last-name",
    type=str,
    callback=validate_lname,
    required=True,
)
def upd(id: int, first_name: str, last_name: str):
    with connect_to_db(load_config()) as db:
        cur = db.cursor()
        result = cur.execute(
            """
            UPDATE customers
            SET
                first_name = COALESCE(?, first_name),
                last_name = COALESCE(?, last_name)
            WHERE id = ? AND is_deleted = FALSE
            RETURNING
                id,
                first_name,
                last_name,
                created_at
            """,
            (
                first_name,
                last_name,
                id,
            ),
        )
        row = cur.fetchall()
        if result.rowcount > 0:
            click.echo("Запись обновлена")
            click.echo(
                tabulate(
                    row,
                    ["id", "first_name", "last_name", "created_at"],
                )
            )
        else:
            click.echo("Запись не найдена")
        db.commit()
        cur.close()


@customers_group.command()
@click.argument("id", type=int, callback=validate_id, required=True)
def rm(id: int):
    with connect_to_db(load_config()) as db:
        cur = db.cursor()
        result = cur.execute(
            """
            UPDATE customers
            SET is_deleted = TRUE
            WHERE id = ?
            RETURNING
                id,
                first_name,
                last_name,
                created_at
            """,
            (id,),
        )
        row = cur.fetchall()
        if result.rowcount > 0:
            click.echo(tabulate(row, ["id", "first_name", "last_name", "created_at"]))
            db.commit()
            click.echo("Запись удалена")
        else:
            click.echo("Запись не найдена")
        cur.close()


@customers_group.command()
@click.argument("id", type=int, callback=validate_id, required=True)
def restore(id: int):
    with connect_to_db(load_config()) as db:
        cur = db.cursor()
        result = cur.execute(
            """
            UPDATE customers
            SET is_deleted = FALSE
            WHERE id = ?
            RETURNING
                id,
                first_name,
                last_name,
                created_at
            """,
            (id,),
        )
        row = cur.fetchall()
        if result.rowcount > 0:
            click.echo(tabulate(row, ["id", "first_name", "last_name", "created_at"]))
            db.commit()
            click.echo("Запись восстановлена")
        else:
            click.echo("Запись не найдена")
        cur.close()


@customers_group.command(name="del")
@click.argument("id", type=int, callback=validate_id, required=True)
@click.option("-y", is_flag=True, default=False)
def _del(id: int, y: bool):
    with connect_to_db(load_config()) as db:
        cur = db.cursor()
        result = cur.execute(
            """
            DELETE FROM customers
            WHERE id = ?
            RETURNING
                id,
                first_name,
                last_name,
                created_at
            """,
            (id,),
        )
        row = cur.fetchall()
        if result.rowcount > 0:
            click.echo(tabulate(row, ["id", "first_name", "last_name", "created_at"]))
            if y:
                db.commit()
                click.echo("Запись уничтожена")
            else:
                if click.confirm("Вы действительно хотите уничтожить эту запись?"):
                    db.commit()
                    click.echo("Запись уничтожена")
                else:
                    db.rollback()
                    click.echo("Уничтожение отменено")
        else:
            click.echo("Запись не найдена")
        cur.close()


@customers_group.command()
@click.option(
    "-q",
    "--query",
    type=str,
    callback=validate_customer_find_query,
    required=True,
)
def find(query: str):
    with connect_to_db(load_config()) as db:
        cur = db.cursor()
        db.create_function("levenshtein", 2, levenshtein)
        cur.execute(
            """
            SELECT
                id,
                first_name,
                last_name,
                levenshtein(first_name || ' ' || last_name, ?) AS rank
            FROM customers
            WHERE rank <= ?
              AND is_deleted = FALSE
            ORDER BY rank ASC
            """,
            (query, 1000),
        )
        row = cur.fetchall()
        click.echo(f"Найдено {len(row)} совпадений")
        click.echo(tabulate(row, ["id", "first_name", "last_name", "rank"]))
        db.commit()
        cur.close()


@customers_group.command()
@click.option("-sr", "--show-removed", is_flag=True, default=False)
@click.option("-l", "--limit", type=int, default=100)
def list(show_removed: bool, limit: int):
    with connect_to_db(load_config()) as db:
        cur = db.cursor()
        cur.execute(
            """
            SELECT
                id,
                first_name,
                last_name,
                is_deleted,
                created_at
            FROM customers
            WHERE is_deleted = ?
            LIMIT ?
            """,
            (show_removed, limit),
        )
        row = cur.fetchall()
        click.echo(f"Найдено {len(row)} записей")
        click.echo(
            tabulate(row, ["id", "first_name", "last_name", "is_deleted", "created_at"])
        )
        db.commit()
        cur.close()
