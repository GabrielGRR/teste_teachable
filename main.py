from datetime import date
from utils.logging_utils import get_logger, setup_logging, log_current_step, yesterday
import scripts.generate_mock_data as generate_mock_data
import scripts.silver as silver
import scripts.gold as gold

logger = get_logger(__name__)

START_DATE=date(2026, 1, 1)
END_DATE=yesterday()


def main():
    setup_logging()

    log_current_step("Generating mock data", logger)
    generate_mock_data.main(START_DATE, END_DATE)
    
    log_current_step("Processing silver layer", logger)
    silver.main()
    
    log_current_step("Processing gold layer", logger)
    gold.main(START_DATE, END_DATE)


if __name__ == "__main__":
    main()