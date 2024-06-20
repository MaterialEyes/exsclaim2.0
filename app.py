#!/lcrc/project/CDIdefect/kvriza_exsclaim/lwashingtoniii-exsclaim2.0/.venv/bin/activate
from functools import wraps
from exsclaim.pipeline import Pipeline


def ntfy(ntfy_link:str, topic:str, on_completion="results", on_error="error"):
    """
	Notify a user about the running of a function.
	:param str ntfy_link: The link to the NTFY server.
	:param str topic: The topic to notify.
	:param str | None on_completion: The message that should be sent when the function has successfully completed.
	Put "results" to send the exact results to the NTFY server.
	:param str | None on_error: The message that should be sent when the function has hit an error and did not finish.
	Put "error" to send the exact error to the NTFY server.
	:return:
	"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            data = None
            try:
                result = func(*args, **kwargs)
                if on_completion is None:
                    return result
                elif on_completion == "results":
                    data = str(result)
                else:
                    data = on_completion
                return result
            except Exception as e:
                if on_error is None:
                    raise e
                elif on_error == "error":
                    from traceback import format_exception
                    data = ' '.join(format_exception(e))
                else:
                    data = on_error
                raise e
            finally:
                if data is None:
                    return

                from requests import post
                post(f"{ntfy_link}/{topic}", data=data)
        return wrapper
    return decorator


@ntfy("https://ntfy.lenwashingtoniii.com", "exsclaim")
def main():
    test_pipeline = Pipeline('./query/nature-ESEM.json')
    results = test_pipeline.run(caption_distributor=True,
                                journal_scraper=True,
                                figure_separator=True,
                                html_scraper=False
                                )
    print(f"{results=}")


if __name__ == "__main__":
    main()
