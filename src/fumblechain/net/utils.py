"""
author: ADG

utilities
"""

import uuid


def get_random_id():
    """Generate and return a random ID.
    Each peer is assigned a unique random ID."""
    return str(uuid.uuid4())
