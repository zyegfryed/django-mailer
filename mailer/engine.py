import time
import logging

from lockfile import FileLock, AlreadyLocked, LockTimeout

from django.conf import settings

try:
    # Django 1.2
    from django.core.mail import get_connection
except ImportError:
    # ImportError: cannot import name get_connection
    from django.core.mail import SMTPConnection
    get_connection = lambda backend=None, fail_silently=False, **kwds: SMTPConnection(fail_silently=fail_silently)
from django.db import transaction

from mailer.models import Message, MessageLog


# when queue is empty, how long to wait (in seconds) before checking again
EMPTY_QUEUE_SLEEP = getattr(settings, "MAILER_EMPTY_QUEUE_SLEEP", 30)

# lock timeout value. how long to wait for the lock to become available.
# default behavior is to never wait for the lock to be available.
LOCK_WAIT_TIMEOUT = getattr(settings, "MAILER_LOCK_WAIT_TIMEOUT", -1)

# The actual backend to use for sending, defaulting to the Django default.
EMAIL_BACKEND = getattr(settings, "MAILER_EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")


def prioritize():
    """
    Yield the messages in the queue in the order they should be sent.
    """

    while True:
        try:
            yield Message.objects.non_deferred().order_by(
                    "priority", "when_added")[0]
        except IndexError:
            # the [0] ref was out of range, so we're done with messages
            break


@transaction.commit_on_success
def mark_as_sent(message):
    """
    Mark the given message as sent in the log and delete the original item.
    """

    MessageLog.objects.log(message, 1)  # @@@ avoid using literal result code
    message.delete()


@transaction.commit_on_success
def mark_as_deferred(message, err=None):
    """
    Mark the given message as deferred in the log and adjust the mail item
    accordingly.
    """

    message.defer()
    logging.info("message deferred due to failure: %s" % err)
    MessageLog.objects.log(message, 3, log_message=str(err))  # @@@ avoid using literal result code


def send_all():
    """
    Send all eligible messages in the queue.
    """

    lock = FileLock(getattr(settings, "MAILER_LOCKFILE", "send_mail"))

    logging.debug("acquiring lock...")
    try:
        lock.acquire(LOCK_WAIT_TIMEOUT)
    except AlreadyLocked:
        logging.debug("lock already in place. quitting.")
        return
    except LockTimeout:
        logging.debug("waiting for the lock timed out. quitting.")
        return
    logging.debug("acquired.")

    start_time = time.time()

    deferred = 0
    sent = 0

    try:
        connection = None
        for message in prioritize():
            try:
                if connection is None:
                    connection = get_connection(backend=EMAIL_BACKEND)
                    # In order for Django to reuse the connection, it has to
                    # already be open() so it sees new_conn_created as False
                    # and does not try and close the connection anyway.
                    connection.open()
                logging.info("sending message '%s' to %s" % (message.subject.encode("utf-8"), u", ".join(message.to_addresses).encode("utf-8")))
                email = message.email
                if not email:
                    # We likely had a decoding problem when pulling it back out
                    # of the database. We should pass on this one.
                    logging.warning("email for message #%d is None. deferring." % message.pk)
                    mark_as_deferred(message, "message.email was None")
                    deferred += 1
                    continue
                email.connection = connection
                email.send()
                mark_as_sent(message)
                sent += 1
            except Exception, err:
                mark_as_deferred(message, err)
                deferred += 1
                # Get new connection, it case the connection itself has an error.
                connection = None
    finally:
        logging.debug("releasing lock...")
        lock.release()
        logging.debug("released.")

    logging.info("")
    logging.info("%s sent; %s deferred;" % (sent, deferred))
    logging.info("done in %.2f seconds" % (time.time() - start_time))


def send_loop():
    """
    Loop indefinitely, checking queue at intervals of EMPTY_QUEUE_SLEEP and
    sending messages if any are on queue.
    """

    while True:
        while not Message.objects.all():
            logging.debug("sleeping for %s seconds before checking queue again" % EMPTY_QUEUE_SLEEP)
            time.sleep(EMPTY_QUEUE_SLEEP)
        send_all()
