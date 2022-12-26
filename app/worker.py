from celery import Celery
from cassandra.cqlengine import connection
from . import (
    config,
    db,
    models,
    Schema,
    crud,
    scraper
)
from celery.schedules import crontab
from cassandra.cqlengine.management import sync_table
from celery.signals import (
    beat_init,
    worker_process_init,
)

celery_app = Celery(__name__)

redis_url = config.get_settings().redis_url

celery_app.conf.broker_url = redis_url
celery_app.conf.result_backend = redis_url

Product = models.Product
ProductScrapeEvent = models.ProductScrapeEvent


def celery_on_startup(*args, **kwargs):
    if connection.cluster is not None:
        connection.cluster.shutdown()
    if connection.session is not None:
        connection.session.shutdown()
    cluster = db.get_cluster()
    session = cluster.connect()
    connection.register_connection(str(session), session=session)
    connection.set_default_connection(str(session))
    sync_table(Product)
    sync_table(ProductScrapeEvent)


beat_init.connect(celery_on_startup)
worker_process_init.connect(celery_on_startup)


def setup_periodic_task(sender, *args, **kwargs):
    # sender.add_periodic_task(1, random_task.s("hello"),expire=10)

    # sender.add_periodic_task(crontab
    #     (hour =8,minute=0,day_of_week=2),
    #     random_task.s("hello"),expire=10
    # )

    sender.add_periodic_task(crontab
                             (minute="*/5",),
                             scrape_products.s()
                             )


@celery_app.task
def random_task(name):
    print(f"who throws a shoe. Honestly {name}.")


@celery_app.task
def list_products():
    q = Product.objects().all().values_list("asin", flat=True)
    print(list(q))


@celery_app.task
def scrape_asin(asin):
    s =  scraper.Scraper(asin=asin,endless_scroll=True)
    dataset = s.scrape()
    print(dataset)
    try:
        validated_data = Schema.ProductListSchema(**dataset)
    except:
        validated_data = None
    if validated_data is not None:
        product, _  = crud.add_scrape_event(validated_data.dict())
        print(asin, product)


@celery_app.task
def scrape_products():
    print("Scraping Products")
    q = Product.objects().all().values_list("asin", flat=True)
    for asin in q:
        scrape_asin.delay(asin)
