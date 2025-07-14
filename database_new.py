import pandas as pd
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
from logging_config import get_logger, log_function_call

load_dotenv()
logger = get_logger(__name__)

class DatabaseManager:
    def __init__(self):
        # PostgreSQL configuration (containerized environment)
        postgres_host = os.getenv('POSTGRES_HOST', 'postgres')
        postgres_port = os.getenv('POSTGRES_PORT', '5432')
        postgres_db = os.getenv('POSTGRES_DB', 'stockanalyst')
        postgres_user = os.getenv('POSTGRES_USER', 'stockanalyst')
        postgres_password = os.getenv('POSTGRES_PASSWORD', 'defaultpassword')
        
        self.db_url = f'postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}'
        logger.info(f"Initializing DatabaseManager with PostgreSQL: {postgres_host}:{postgres_port}/{postgres_db}")
        
        self.engine = create_engine(self.db_url)
        self.create_tables()
        logger.info("DatabaseManager initialized successfully")