import os
import io

from django.core.cache import cache
from celery.task import Task

import logging

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')


try:
    from celery.utils.log import get_task_logger
except ImportError:
    from celery.log import get_task_logger


from .conf import settings
from .signals import file_transferred
from .utils import import_attribute

logger = get_task_logger(name=__name__)


class Transfer(Task):
    """
    The default task. Transfers a file to a remote location.
    The actual transfer is implemented in the remote backend.

    To use a different task, pass it into the backend:

    .. code-block:: python

        from queued_storage.backends import QueuedS3BotoStorage

        s3_delete_storage = QueuedS3BotoStorage(
            task='queued_storage.tasks.TransferAndDelete')

        # later, in model definition:
        image = models.ImageField(storage=s3_delete_storage)


    The result should be ``True`` if the transfer was successful,
    or ``False`` if unsuccessful. In the latter case the task will be
    retried.

    You can subclass the :class:`~queued_storage.tasks.Transfer` class
    to customize the behaviour, to do something like this:

    .. code-block:: python

        from queued_storage.tasks import Transfer

        class TransferAndNotify(Transfer):
            def transfer(self, *args, **kwargs):
                result = super(TransferAndNotify, self).transfer(*args, **kwargs)
                if result:
                    # call the (imaginary) notify function with the result
                    notify(result)
                return result

    """
    #: The number of retries if unsuccessful (default: see
    #: :attr:`~queued_storage.conf.settings.QUEUED_STORAGE_RETRIES`)
    max_retries = settings.QUEUED_STORAGE_RETRIES

    #: The delay between each retry in seconds (default: see
    #: :attr:`~queued_storage.conf.settings.QUEUED_STORAGE_RETRY_DELAY`)
    default_retry_delay = settings.QUEUED_STORAGE_RETRY_DELAY

    def run(self, name, cache_key,
            local_path, remote_path,
            local_options, remote_options, **kwargs):
        """
        The main work horse of the transfer task. Calls the transfer
        method with the local and remote storage backends as given
        with the parameters.

        :param name: name of the file to transfer
        :type name: str
        :param local_path: local storage class to transfer from
        :type local_path: str
        :param local_options: options of the local storage class
        :type local_options: dict
        :param remote_path: remote storage class to transfer to
        :type remote_path: str
        :param remote_options: options of the remote storage class
        :type remote_options: dict
        :param cache_key: cache key to set after a successful transfer
        :type cache_key: str
        :rtype: task result
        """
        local = import_attribute(local_path)(**local_options)
        remote = import_attribute(remote_path)(**remote_options)
        result = self.transfer(name, local, remote, **kwargs)

        if result is True:
            cache.set(cache_key, True)
            file_transferred.send(sender=self.__class__,
                                  name=name, local=local, remote=remote)
        elif result is False:
            args = [name, cache_key, local_path,
                    remote_path, local_options, remote_options]
            self.retry(args=args, kwargs=kwargs)
        else:
            raise ValueError("Task '%s' did not return True/False but %s" %
                             (self.__class__, result))
        return result

    def transfer(self, name, local, remote, **kwargs):
        """
        Transfers the file with the given name from the local to the remote
        storage backend.

        :param name: The name of the file to transfer
        :param local: The local storage backend instance
        :param remote: The remote storage backend instance
        :returns: `True` when the transfer succeeded, `False` if not. Retries
                  the task when returning `False`
        :rtype: bool
        """
        try:
            remote.save(name, local.open(name))
            return True
        except Exception as e:
            logger.error("Unable to save '%s' to remote storage. "
                         "About to retry." % name)
            logger.exception(e)
            return False


class TransferAndDelete(Transfer):
    """
    A :class:`~queued_storage.tasks.Transfer` subclass which deletes the
    file with the given name using the local storage if the transfer
    was successful.
    """
    def generate_text_filename(self, filename):
        newfilename = str(filename).replace("audios/", "texts/")
        # newfilename = str(newfilename).replace(".wav", ".txt")
        return newfilename
        # [END speech_transcribe_auto_punctuation_beta]

    # function to remove arbitrary character after filename. The
    # correct filename should be interview_7_candidate_5_question_8_lang_en-US
    def get_clean_name(self, file_name):
        if len(file_name.split('_')) == 9:
            return "_".join(file_name.split('_')[:-1])
        else:
            return file_name

    def transfer(self, name, local, remote, **kwargs):
        name = self.get_clean_name(name)
        # print("Begin transfer of {0}".format(name))
        logging.info("Begin transfer of {0}".format(name))
        result = super(TransferAndDelete, self).transfer(name, local, remote, **kwargs)
        if result:
            local.delete(name)
        logging.info("Completed transfer of {0}".format(name))
        return result
