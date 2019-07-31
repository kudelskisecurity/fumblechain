#!/usr/bin/env python3

"""FumbleStore lessons"""

from dataclasses import dataclass


@dataclass
class Lesson:
    id: int
    title: str
    template_path: str


def get_available_lessons():
    """Returns the list of available lessons."""
    lessons = {
        "About Fumblechain": [
            Lesson(0, "Introduction to FumbleChain", "lessons/fumblechain.html"),
            Lesson(1, "Using the FumbleChain CLI", "lessons/fumblechain-cli.html"),
            Lesson(2, "Using the Blockchain explorer", "lessons/blockchain-explorer.html"),
            Lesson(3, "Using the WebWallet", "lessons/web-wallet.html"),
            Lesson(4, "Scripting with scli", "lessons/scli.html"),
            Lesson(5, "Network messages", "lessons/fumblechain-network-messages.html")
        ],
        "Blockchain theory": [
            Lesson(999, "What is a blockchain?", "lessons/what-is-a-blockchain.html"),
            Lesson(1000, "Consensus mechanisms", "lessons/consensus-mechanisms.html"),
            Lesson(1001, "Wallet balance models: Account vs UTXO", "lessons/wallet-balance.html"),
            Lesson(1002, "What's in a block?", "lessons/block-headers.html"),
            Lesson(1003, "Blockchain state synchronization", "lessons/blockchain-synchronization.html"),
            Lesson(1004, "Smart contracts and DApps", "lessons/smart-contracts.html")

        ],
        "Blockchain vulnerabilities and exploitation": [
            Lesson(2000, "Transaction input validation", "lessons/tx-input-validation.html"),
            Lesson(2001, "Other-chain replay attacks", "lessons/other-chain-replay-attacks.html"),
            Lesson(2002, "Same-chain replay attacks", "lessons/same-chain-replay-attacks.html"),
            Lesson(2003, "Public key and address mismatch attacks",
                   "lessons/pubkey-address-mismatch-attacks.html"),
            Lesson(2004, "Floating-point underflow/overflow attacks",
                   "lessons/floating-point-underflow-overflow-attacks.html"),
            Lesson(2005, "Denial of service attacks", "lessons/dos-attacks.html"),
            Lesson(2006, "Wallet-side validation attacks", "lessons/wallet-side-validation-attacks.html"),
            Lesson(2007, "Attacks on public-key cryptosystems", "lessons/attacks-on-public-key-cryptosystems.html")
        ],
        "Contributing to FumbleChain": [
            Lesson(10001, "Basics of contributing", "lessons/basics-contributing.html"),
            Lesson(10002, "Creating a new FumbleStore lesson", "lessons/new-lessons.html"),
            Lesson(10003, "Creating a new FumbleStore challenge", "lessons/new-challenges.html")
        ]
    }

    return lessons
