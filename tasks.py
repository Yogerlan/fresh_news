import logging

from robocorp.tasks import task
from RPA.Robocorp.WorkItems import WorkItems


@task
def news_collector():
    try:
        wi = WorkItems()
        wi.get_input_work_item()

        for key, value in wi.get_work_item_variables().items():
            logging.info(f"{key} = {value}")
    except Exception as ex:
        logging.info("No workitems.")
