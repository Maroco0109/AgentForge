"""File reader for CSV, Excel, JSON files."""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class FileReadResult:
    """Result of reading a file."""

    path: str
    file_type: str
    row_count: int = 0
    columns: list[str] = field(default_factory=list)
    data: list[dict] = field(default_factory=list)
    error: str | None = None
    success: bool = True


class FileReader:
    """Read data from various file formats."""

    SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".json", ".jsonl"}

    def read(self, file_path: str) -> FileReadResult:
        """Read a file and return structured data."""
        path = Path(file_path)

        if not path.exists():
            return FileReadResult(
                path=file_path, file_type="", error="File not found", success=False
            )

        ext = path.suffix.lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            return FileReadResult(
                path=file_path,
                file_type=ext,
                error=f"Unsupported file type: {ext}",
                success=False,
            )

        try:
            if ext == ".csv":
                return self._read_csv(path)
            elif ext in (".xlsx", ".xls"):
                return self._read_excel(path)
            elif ext == ".json":
                return self._read_json(path)
            elif ext == ".jsonl":
                return self._read_jsonl(path)
            else:
                return FileReadResult(
                    path=file_path, file_type=ext, error="Unsupported", success=False
                )
        except Exception as e:
            return FileReadResult(path=file_path, file_type=ext, error=str(e), success=False)

    def _read_csv(self, path: Path) -> FileReadResult:
        import pandas as pd

        df = pd.read_csv(path)
        return FileReadResult(
            path=str(path),
            file_type="csv",
            row_count=len(df),
            columns=list(df.columns),
            data=df.head(1000).to_dict(orient="records"),
        )

    def _read_excel(self, path: Path) -> FileReadResult:
        import pandas as pd

        df = pd.read_excel(path)
        return FileReadResult(
            path=str(path),
            file_type="excel",
            row_count=len(df),
            columns=list(df.columns),
            data=df.head(1000).to_dict(orient="records"),
        )

    def _read_json(self, path: Path) -> FileReadResult:
        with open(path) as f:
            raw = json.load(f)

        if isinstance(raw, list):
            data = raw[:1000]
            columns = list(data[0].keys()) if data and isinstance(data[0], dict) else []
            return FileReadResult(
                path=str(path),
                file_type="json",
                row_count=len(raw),
                columns=columns,
                data=data,
            )
        elif isinstance(raw, dict):
            return FileReadResult(
                path=str(path),
                file_type="json",
                row_count=1,
                columns=list(raw.keys()),
                data=[raw],
            )
        else:
            return FileReadResult(
                path=str(path),
                file_type="json",
                error="Unexpected JSON structure",
                success=False,
            )

    def _read_jsonl(self, path: Path) -> FileReadResult:
        data = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    data.append(json.loads(line))
                if len(data) >= 1000:
                    break

        columns = list(data[0].keys()) if data and isinstance(data[0], dict) else []
        return FileReadResult(
            path=str(path),
            file_type="jsonl",
            row_count=len(data),
            columns=columns,
            data=data,
        )
