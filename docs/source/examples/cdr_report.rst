Run a CDR Report
================
This script demonstrates how to create a CDR report and download all the lines from the report into a list, where the
lines can be processed.

.. code-block:: python

    import wxcadm
    import time

    webex_access_token = "Your Webex API Access Token"
    cdr_template_title = 'Calling Detailed Call History'
    report_start = '2022-08-01'
    report_end = '2022-08-31'

    # Connect to Webex. You can use fast_mode=True since we won't be dealing with user phone numbers
    webex = wxcadm.Webex(webex_access_token)

    # Loop through the report templates to find the CDR report
    for template in webex.org.reports.templates:
        if template['title'] == cdr_template_title:
            cdr_template = template['Id']

    # Create the report and get the ID generated
    report_id = webex.org.reports.create_report(cdr_template, start_date=report_start, end_date=report_end)

    # Start a loop to check the report status and wait for it to be "done"
    report_status = 'unknown'
    while report_status != 'done':
        time.sleep(60)    # Wait between status checks. Anything less than a minute is overkill.
        report_status = webex.org.reports.report_status(report_id)

    # Now that the report is done, get the report lines
    report_lines = webex.org.reports.get_report_lines(report_id)

    # Now you have the entire report, including headers in report_lines[0] and can do whatever you want
    for line in report_lines:
        print(line)

Since 3.0.3, you can also use the :py:meth:`Reports.cdr_report()` method to create a CDR Report

.. code-block:: python

    import wxcadm
    import time

    webex_access_token = "Your Webex API Access Token"
    num_days = 30

    # Connect to Webex. You can use fast_mode=True since we won't be dealing with user phone numbers
    webex = wxcadm.Webex(webex_access_token)

    # Create the report and get the ID generated
    report_id = webex.org.reports.cdr_report(days=num_days)

    # Start a loop to check the report status and wait for it to be "done"
    report_status = 'unknown'
    while report_status != 'done':
        time.sleep(60)    # Wait between status checks. Anything less than a minute is overkill.
        report_status = webex.org.reports.report_status(report_id)

    # Now that the report is done, get the report lines
    report_lines = webex.org.reports.get_report_lines(report_id)

    # Now you have the entire report, including headers in report_lines[0] and can do whatever you want
    for line in report_lines:
        print(line)

