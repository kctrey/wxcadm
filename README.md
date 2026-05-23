# wxcadm (DEPRECATED)

> **NOTICE: This project is officially deprecated as of May 2026.**

## The Future of Webex Administration
`wxcadm` was created as an early, easy-to-use wrapper for Webex Calling administrators to automate tasks via Python. Since its inception, the ecosystem has evolved, and far more robust, professionally maintained tools are now available. 

To ensure the best possible experience and security for your automation workflows, **all users are strongly encouraged to migrate to [wxc-sdk](https://github.com/jeokrohn/wxc_sdk).**

## Why Migrate?
*   **Ongoing Support:** `wxc-sdk` is the modern standard for Python-based Webex administration.
*   **Feature Completeness:** It covers the full breadth of the Webex APIs, whereas `wxcadm` only handled a limited subset.
*   **AI-Ready:** Modern LLMs have extensive training on the current `wxc-sdk` structure, making it significantly easier to generate and maintain your scripts using AI.

## Migration Guide: Use AI to Rewrite Your Scripts
You do not need to rewrite your automation manually. You can leverage AI to perform the conversion for you. Use the following prompt format to transition your existing `wxcadm` logic to `wxc-sdk`:

> *"I have a legacy Python script that currently uses the `wxcadm` module to perform the following task: [PASTE YOUR CODE HERE]. Please rewrite this script to use the modern `wxc-sdk` library instead. Ensure the authentication and API calls follow the current `wxc-sdk` best practices."*

## Status
*   **Maintenance:** This repository is now **Read-Only**. No new features, bug fixes, or security patches will be provided.
*   **Support:** Please redirect all future questions and issues to the [official wxc-sdk repository](https://github.com/jeokrohn/wxc_sdk).
