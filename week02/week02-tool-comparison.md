# Week 2 — AI Tool Comparison
 
## The requirement
(one paragraph)
 
## Prompts used
### Claude
Write me a contact form. The form must have name, email, and message. Validate that the email is a valid email on the server-side. The form should reject empty name spaces or empty message fields with a visible error. A successful entry should show a confirmation page.
### Gemini
Write me a contact form. The form must have name, email, and message. Validate that the email is a valid email on the server-side. The form should reject empty name spaces or empty message fields with a visible error. A successful entry should show a confirmation page.
 
## Scores
| Criterion    | Claude | Gemini |
|--------------|--------|--------|
| Correctness  |   5    |    4   |

- Gemini: Yes the application runs well. Although a little basic in its UI design. Each function works. Each error catcher works in every scenario.
- Claude: Yes the application works well. The application UI is a sleaker/cleaner look. All fucntions work. The error messages are also clear in what was wrong and also provides examples like how an email address hsould be written.

| Code quality |    4   |    3   |

- Gemini: No long lined functions. Code reads quite well. Although I had to include more comments in teh next prompt for each function.
- Claude: One long page of code instead of seperate pages for HTML, css etc. This makes the code a little hard to follow. But the code was extremly well commented without any indication from me the developer in the initial prompt. 

| Completeness |   5    |    5   |

- Gemini: Worked with every error case in each scenario. I couldnt find a fault in that.
- Claude: Like Gemini, it worked with every error case in each scenario. I couldnt find a fault in that.

| Security     |    3   |    2   |

- Gemini: 'debug=True' was included. This is a debbugging tool used by developers to catch errors in testing. It also can contain sensitive vulnerabilitys that a attacker could use. This could be skipped over if a user generates this application with AI.
- Claude: Liek Gemini it also included the 'debug=True' code which is a bad vulnerability in the code. But unlike Gemini even after the extra commenting prompt, Claude included detailed information in the comment for that code that it is a vulnerability to release this code in a production enviroment. 
 
## What each got wrong
- Gemini: The code was a little unreadable upon the first prompt. Adding a 2nd prompt asking fopr more cod comments helped. I now see the security threat of 'debug=True'. This is a threat vulerability that could easily be missed by inexpirenced developers. Gemini also gave me 2 options for installing the application. The Node.js option was a little confusing to be thrown at. The applications UI also was not very pretty, this would have to be mentioned in the following prompts.
- Claude: One huge .py file that included the whole code base made the code a little unclear. Everything else was fine.
 
## Which I kept, and why
- Gemini: The Criterion and Complteness for the application worked well. The application ran with no visable faults. Each error path worked correctly. The application just didnt look very pretty. The code generally seemed pretty good. The functions were not over complicated.
- l: The UI & UX was good. It worked functionally well in all testing scenarios and although still basic, the UI was nicer than Gemini. The code was also well documented and commented. It expalined each of the GET fucntions at the beginning of the code.
