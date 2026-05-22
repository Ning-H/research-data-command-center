from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql://research:research@localhost:5432/research_command_center"
    duckdb_path: str = "storage/duckdb/research_command_center.duckdb"
    raw_storage_root: str = "storage/raw"
    parquet_storage_root: str = "storage/parquet"
    object_storage_root: str = "storage/object_store"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
