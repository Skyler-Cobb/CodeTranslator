# codec.py

"""
Legacy entrypoint for other modules. We simply re-export from helpers.codec now.
"""

from helpers.codec import (
    decode_message_with_module,
    encode_message_with_module,
    tokenize_message_with_module,
    multi_step_decode,
    multi_step_encode,
)
