"""Pipeline error types."""


class PipelineError(Exception):
    """Base pipeline error."""

    def __init__(self, code: str, message: str, details: dict = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> dict:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details
            }
        }


class ProbeError(PipelineError):
    """FFprobe validation failed."""

    def __init__(self, message: str, details: dict = None):
        super().__init__("FFPROBE_FAILED", message, details)


class ExtractAudioError(PipelineError):
    """Audio extraction failed."""

    def __init__(self, message: str, details: dict = None):
        super().__init__("EXTRACT_AUDIO_FAILED", message, details)


class ChunkAudioError(PipelineError):
    """Audio chunking failed."""

    def __init__(self, message: str, details: dict = None):
        super().__init__("CHUNK_AUDIO_FAILED", message, details)


class TranscribeError(PipelineError):
    """Transcription failed."""

    def __init__(self, message: str, details: dict = None):
        super().__init__("TRANSCRIBE_FAILED", message, details)


class TranslateError(PipelineError):
    """Translation failed."""

    def __init__(self, message: str, details: dict = None):
        super().__init__("TRANSLATE_FAILED", message, details)


class SRTError(PipelineError):
    """SRT generation failed."""

    def __init__(self, message: str, details: dict = None):
        super().__init__("SRT_GENERATION_FAILED", message, details)


class RenderError(PipelineError):
    """Hardsub render failed."""

    def __init__(self, message: str, details: dict = None):
        super().__init__("RENDER_FAILED", message, details)
