from celery import Celery


app = Celery(
    "whip_celery",
    include=["app.libs.tasks"],
)

app.config_from_object("app.config.celeryconfig")


if __name__ == "__main__":
    app.run()
