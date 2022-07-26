import base64
import logging
import uuid

__all__ = ['decode_spark_id', 'console_logging', 'tracking_id']

def decode_spark_id(id: str):
    """ Decode the Webex ID to obtain the Spark ID

    Note that the returned string is the full URI, like
        ```ciscospark://us/PEOPLE/5b7ddefe-cc47-496a-8df0-18d8e4182a99```. In most cases, you only care about the ID
        at the end, so a ```.split('/')[-1]``` can be used to ontain that.

    Args:
        id (str): The Webex ID (base64 encoded string)

    Returns:
        str: The Spark ID

    """
    id_bytes = base64.b64decode(id + "==")
    spark_id: str = id_bytes.decode("utf-8")
    return spark_id


def tracking_id():
    id = f"WXCADM_{uuid.uuid4()}"
    return id

