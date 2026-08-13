import logging
from contextlib import contextmanager
from tqdm import tqdm


__all__ = ["tqdm_logging_redirect"]


class _TqdmHandler(logging.Handler):
	def emit(self, record):
		try:
			msg = self.format(record)
			tqdm.write(msg)
		except Exception:
			self.handleError(record)


@contextmanager
def tqdm_logging_redirect(logger: logging.Logger):
	# walk up through propagating ancestors too
	loggers = [logger]
	parent = logger.parent
	while parent is not None:
		loggers.append(parent)
		if not parent.propagate:
			break
		parent = parent.parent

	originals = []
	tqdm_handler = _TqdmHandler()
	for lg in loggers:
		originals.append((lg, list(lg.handlers)))
		for i, handler in lg.handlers:
			if isinstance(handler, logging.StreamHandler):
				tqdm_handler.setFormatter(handler.formatter)
				lg.handlers[i] = tqdm_handler
		lg.handlers = [tqdm_handler]

	try:
		yield logger
	finally:
		for lg, handlers in originals:
			lg.handlers = handlers
