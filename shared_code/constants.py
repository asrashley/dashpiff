"""
Global constants
"""
import binascii

# HTTP headers to not copy from origin response
EXCLUDED_HTTP_HEADERS = set({'content-length', 'connection'})

# UUID of the sample encryption data used by the PIFF standard
PIFF_UUID = binascii.a2b_hex("a2394f525a9b4f14a2446c427c648df4")

# The "free" box type in UUID form. See section 11.1 of ISO 14496-12
FREE_UUID = binascii.a2b_hex("6672656500110010800000AA00389B71")

