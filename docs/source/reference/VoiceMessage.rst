.. py:currentmodule:: wxcadm.person

The VoiceMessage class
======================
The VoiceMessage class provides access to Webex Calling Voice Messages (i.e. Voicemail).

VoiceMessage instances are instantiated with the :py:meth:`Me.get_voice_messages()` method and are not created directly.

.. note::

    Voice Message access is limited to the token owner only. An administrator token does not have access to other
    user's Voice Messages.

.. autoclass:: wxcadm.person.VoiceMessage
    :members:
    :undoc-members:
