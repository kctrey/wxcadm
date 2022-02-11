Logging
=======
By default, the module logs to ``wxcadm.log``. Logging defaults to the ``INFO`` level, which shows API call summary
information. To change the logging level, call the :meth:`wxcadm.set_logging_level()` method with the desired logging
level. The ``DEBUG`` level is useful for seeing detailed API processing, or the logs can be disabled with the ``NONE``
level.

Set Debug Logging
-----------------

.. code-block:: python

    import wxcadm

    wxcadm.set_logging_level("debug")
    # or #
    wxcadm.set_logging_level("none")

