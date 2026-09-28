"""
Structured catalog of email categories and scenarios.
This is the single source of truth for what scenarios exist. The dataset
generator (generate_dataset.py) reads this to build golden_set.jsonl, and
`export_categories.py` turns it into the JSON the frontend/backend serve
at GET /api/categories. Add new scenarios here, not in the frontend.
"""

CATEGORIES = [
    {
        "id": "university",
        "label": "University",
        "emoji": "🎓",
        "scenarios": [
            {
                "id": "deadline_extension",
                "label": "Ask professor for deadline extension",
                "recipient": "Professor",
                "purpose": "Request a short extension on an assignment deadline",
                "required_information": [
                    "Apologize for the inconvenience",
                    "Explain the reason for the delay",
                    "Request a specific new deadline",
                    "Thank the professor",
                ],
            },
            {
                "id": "ask_about_grade",
                "label": "Ask professor about a grade",
                "recipient": "Professor",
                "purpose": "Politely ask for clarification on a grade received",
                "required_information": [
                    "Reference the specific assignment/exam",
                    "Ask which parts lost points",
                    "Request a time to discuss",
                    "Remain respectful of the grading decision",
                ],
            },
            {
                "id": "recommendation_letter",
                "label": "Request a recommendation letter",
                "recipient": "Professor",
                "purpose": "Ask a professor to write a recommendation letter",
                "required_information": [
                    "State the purpose of the letter (job/grad school)",
                    "Give the submission deadline",
                    "Offer to provide a resume/transcript",
                    "Thank the professor for considering",
                ],
            },
            {
                "id": "assignment_clarification",
                "label": "Ask for clarification about an assignment",
                "recipient": "Professor",
                "purpose": "Clarify an ambiguous requirement in an assignment",
                "required_information": [
                    "Reference the specific assignment",
                    "State exactly what is unclear",
                    "Ask a direct question",
                    "Thank the professor for their time",
                ],
            },
            {
                "id": "missed_class_apology",
                "label": "Apologize for missing class",
                "recipient": "Professor",
                "purpose": "Apologize for an absence and ask what was missed",
                "required_information": [
                    "Apologize for missing the class",
                    "Briefly state the reason",
                    "Ask what material/announcements were missed",
                    "Offer to catch up independently",
                ],
            },
            {
                "id": "request_meeting",
                "label": "Request a meeting",
                "recipient": "Professor",
                "purpose": "Request office hours or a one-on-one meeting",
                "required_information": [
                    "State the topic to discuss",
                    "Propose two possible time windows",
                    "Ask for a confirmation",
                ],
            },
            {
                "id": "submit_late_work",
                "label": "Submit late work",
                "recipient": "Professor",
                "purpose": "Submit an assignment after the deadline with an explanation",
                "required_information": [
                    "State the assignment is attached/submitted",
                    "Acknowledge it is late",
                    "Briefly explain why",
                    "Accept any late penalty",
                ],
            },
            {
                "id": "thank_professor",
                "label": "Thank a professor",
                "recipient": "Professor",
                "purpose": "Thank a professor for their help or mentorship",
                "required_information": [
                    "Mention the specific help received",
                    "Explain the impact it had",
                    "Express genuine thanks",
                ],
            },
        ],
    },
    {
        "id": "internship",
        "label": "Internship & Jobs",
        "emoji": "💼",
        "scenarios": [
            {
                "id": "internship_application",
                "label": "Internship application",
                "recipient": "Hiring manager",
                "purpose": "Apply for an advertised internship position",
                "required_information": [
                    "State the position title",
                    "Mention relevant skills/experience",
                    "Reference attached resume",
                    "Express enthusiasm for the role",
                ],
            },
            {
                "id": "follow_up_application",
                "label": "Follow up after application",
                "recipient": "Recruiter",
                "purpose": "Follow up on a submitted application with no response",
                "required_information": [
                    "Reference the position and application date",
                    "Politely ask for a status update",
                    "Reaffirm interest",
                ],
            },
            {
                "id": "interview_thank_you",
                "label": "Interview thank-you",
                "recipient": "Interviewer",
                "purpose": "Thank the interviewer after an interview",
                "required_information": [
                    "Thank them for their time",
                    "Reference a specific topic discussed",
                    "Reaffirm interest in the role",
                ],
            },
            {
                "id": "application_status",
                "label": "Ask about application status",
                "recipient": "Recruiter",
                "purpose": "Ask about the status of a pending application",
                "required_information": [
                    "Reference the role applied to",
                    "Ask for an update politely",
                    "Offer to provide more information if needed",
                ],
            },
            {
                "id": "contact_recruiter",
                "label": "Contact a recruiter",
                "recipient": "Recruiter",
                "purpose": "Introduce yourself to a recruiter about open roles",
                "required_information": [
                    "Briefly introduce yourself",
                    "State the type of role you're seeking",
                    "Mention relevant background",
                    "Ask about next steps",
                ],
            },
            {
                "id": "request_referral",
                "label": "Request a referral",
                "recipient": "Former colleague",
                "purpose": "Ask a contact for a referral at their company",
                "required_information": [
                    "State the specific role and company",
                    "Explain why you're a good fit",
                    "Make the ask low-pressure",
                    "Offer to send resume/details",
                ],
            },
            {
                "id": "internship_opportunities",
                "label": "Ask about internship opportunities",
                "recipient": "Company contact",
                "purpose": "Ask whether a company has upcoming internship openings",
                "required_information": [
                    "Introduce yourself briefly",
                    "State your field of study",
                    "Ask about upcoming openings",
                ],
            },
            {
                "id": "networking_follow_up",
                "label": "Follow up after networking",
                "recipient": "Networking contact",
                "purpose": "Follow up with someone met at a networking event",
                "required_information": [
                    "Reference where you met",
                    "Recall a specific conversation point",
                    "Propose staying in touch or a call",
                ],
            },
        ],
    },
    {
        "id": "professional",
        "label": "Professional",
        "emoji": "🏢",
        "scenarios": [
            {
                "id": "schedule_meeting",
                "label": "Schedule a meeting",
                "recipient": "Colleague",
                "purpose": "Propose a meeting time to discuss a work topic",
                "required_information": [
                    "State the meeting purpose",
                    "Propose a date/time",
                    "Ask for confirmation",
                ],
            },
            {
                "id": "reschedule_meeting",
                "label": "Reschedule a meeting",
                "recipient": "Colleague",
                "purpose": "Ask to move an already-scheduled meeting",
                "required_information": [
                    "Reference the original meeting",
                    "Apologize for the change",
                    "Propose a new time",
                ],
            },
            {
                "id": "cancel_meeting",
                "label": "Cancel a meeting",
                "recipient": "Colleague",
                "purpose": "Cancel a scheduled meeting",
                "required_information": [
                    "Reference the meeting being cancelled",
                    "Give a brief reason",
                    "Offer to reschedule",
                ],
            },
            {
                "id": "request_information",
                "label": "Request information",
                "recipient": "Colleague",
                "purpose": "Ask a colleague for specific work-related information",
                "required_information": [
                    "State exactly what information is needed",
                    "Explain why it's needed",
                    "Give a deadline if relevant",
                ],
            },
            {
                "id": "follow_up_unanswered",
                "label": "Follow up on an unanswered email",
                "recipient": "Colleague",
                "purpose": "Politely follow up on a previous email with no reply",
                "required_information": [
                    "Reference the original email/date",
                    "Restate the ask briefly",
                    "Remain polite, not pushy",
                ],
            },
            {
                "id": "project_update",
                "label": "Send a project update",
                "recipient": "Manager",
                "purpose": "Send a status update on a project",
                "required_information": [
                    "Summarize progress so far",
                    "Flag any blockers",
                    "State next steps",
                ],
            },
            {
                "id": "professional_clarification",
                "label": "Ask for clarification",
                "recipient": "Manager",
                "purpose": "Ask a manager to clarify an ambiguous instruction",
                "required_information": [
                    "Reference the instruction/task",
                    "State exactly what's unclear",
                    "Ask a direct question",
                ],
            },
            {
                "id": "apologize_delay",
                "label": "Apologize for a delay",
                "recipient": "Client",
                "purpose": "Apologize for a delayed deliverable",
                "required_information": [
                    "Apologize clearly",
                    "Briefly explain the cause",
                    "Give a new delivery date",
                ],
            },
        ],
    },
    {
        "id": "customer_service",
        "label": "Customer Service",
        "emoji": "📞",
        "scenarios": [
            {
                "id": "request_refund",
                "label": "Request a refund",
                "recipient": "Customer support",
                "purpose": "Request a refund for a purchased product/service",
                "required_information": [
                    "Reference the order/transaction",
                    "State the reason for the refund",
                    "State the desired outcome (refund amount)",
                ],
            },
            {
                "id": "make_complaint",
                "label": "Make a complaint",
                "recipient": "Customer support",
                "purpose": "File a complaint about a product/service issue",
                "required_information": [
                    "Describe the issue clearly",
                    "Reference order/account details",
                    "State the desired resolution",
                ],
            },
            {
                "id": "ask_for_information",
                "label": "Ask for information",
                "recipient": "Customer support",
                "purpose": "Ask a company for information about a product/service",
                "required_information": [
                    "State the specific question",
                    "Reference the relevant product",
                    "Ask for a timely response",
                ],
            },
            {
                "id": "cancel_appointment",
                "label": "Cancel an appointment",
                "recipient": "Service provider",
                "purpose": "Cancel a scheduled appointment",
                "required_information": [
                    "Reference the appointment date/time",
                    "State it's being cancelled",
                    "Apologize for any inconvenience",
                ],
            },
            {
                "id": "reschedule_appointment",
                "label": "Reschedule an appointment",
                "recipient": "Service provider",
                "purpose": "Ask to move a scheduled appointment",
                "required_information": [
                    "Reference the original appointment",
                    "Propose a new time",
                    "Apologize for the change",
                ],
            },
            {
                "id": "report_problem",
                "label": "Report a problem",
                "recipient": "Customer support",
                "purpose": "Report a technical or service problem",
                "required_information": [
                    "Describe the problem clearly",
                    "State when it started",
                    "Ask for a fix or next steps",
                ],
            },
            {
                "id": "request_support",
                "label": "Request support",
                "recipient": "Customer support",
                "purpose": "Ask for help resolving an issue with a product",
                "required_information": [
                    "Describe the issue",
                    "Mention troubleshooting already tried",
                    "Ask for guidance",
                ],
            },
            {
                "id": "thank_support",
                "label": "Thank customer support",
                "recipient": "Customer support",
                "purpose": "Thank a support agent for resolving an issue",
                "required_information": [
                    "Reference the issue that was resolved",
                    "Thank the specific agent/team",
                    "Note the positive experience",
                ],
            },
        ],
    },
]

TONES = [
    "Professional and respectful",
    "Warm and friendly",
    "Formal and concise",
    "Polite but firm",
    "Apologetic and humble",
]

CONTEXTS_BY_CATEGORY = {
    "university": [
        "My laptop stopped working and I could not finish the assignment.",
        "I had a family emergency that required me to travel unexpectedly.",
        "I was hospitalized for a few days and missed coursework.",
        "I am juggling three exams in the same week and fell behind.",
        "I misread the syllabus and only just realized the deadline.",
        "I was sick with the flu for several days.",
    ],
    "internship": [
        "I applied two weeks ago through the company's careers page.",
        "I met the recruiter at a career fair last month.",
        "A former colleague referred me to this opening.",
        "I have relevant coursework and a personal project in this area.",
        "I interviewed for the role last week.",
        "I saw the opportunity posted on LinkedIn.",
    ],
    "professional": [
        "The project deadline moved up unexpectedly this week.",
        "A key vendor delivery was delayed, affecting the timeline.",
        "Two other meetings ended up overlapping with this one.",
        "The scope of the task changed after the last discussion.",
        "I need the data before I can finish my part of the report.",
        "I'm out of office part of next week and need to plan around it.",
    ],
    "customer_service": [
        "The product arrived damaged when it was delivered.",
        "I was charged twice for the same order.",
        "The service stopped working after the latest update.",
        "I need to change my plans due to a scheduling conflict.",
        "The item I received does not match the description online.",
        "I haven't received any confirmation since I placed the order.",
    ],
}

MAX_LENGTHS = ["Short (under 120 words)", "Medium (120-200 words)", "Concise, 3-4 sentences"]
