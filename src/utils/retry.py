from tenacity import retry, wait_exponential_jitter, stop_after_attempt, retry_if_exception_type
import requests

Retryable = retry(
    wait=wait_exponential_jitter(initial=1, max=20),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type((requests.exceptions.Timeout, requests.exceptions.RequestException)),
    reraise=True
)
