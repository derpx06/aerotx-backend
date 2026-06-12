from enum import StrEnum


class JobStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    LLM_PROCESSING = "LLM_PROCESSING"
    REPORTING = "REPORTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            val_upper = value.upper()
            for member in cls:
                if member.value == val_upper:
                    return member
        return None


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            val_upper = value.upper()
            for member in cls:
                if member.value == val_upper:
                    return member
        return None


class JobEventType(StrEnum):
    JOB_CREATED = "JOB_CREATED"
    FILE_UPLOADED = "FILE_UPLOADED"
    VALIDATION_STARTED = "VALIDATION_STARTED"
    VALIDATION_COMPLETED = "VALIDATION_COMPLETED"
    CLEANING_STARTED = "CLEANING_STARTED"
    CLEANING_COMPLETED = "CLEANING_COMPLETED"
    ANOMALY_DETECTION_STARTED = "ANOMALY_DETECTION_STARTED"
    ANOMALY_DETECTION_COMPLETED = "ANOMALY_DETECTION_COMPLETED"
    CLASSIFICATION_STARTED = "CLASSIFICATION_STARTED"
    CLASSIFICATION_COMPLETED = "CLASSIFICATION_COMPLETED"
    SUMMARY_GENERATION_STARTED = "SUMMARY_GENERATION_STARTED"
    SUMMARY_GENERATION_COMPLETED = "SUMMARY_GENERATION_COMPLETED"
    JOB_COMPLETED = "JOB_COMPLETED"
    JOB_FAILED = "JOB_FAILED"

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            val_upper = value.upper()
            for member in cls:
                if member.value == val_upper:
                    return member
        return None
