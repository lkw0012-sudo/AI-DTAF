# DTAF
2/05/2026: Updated files found in DTCCylce.

Added the file reader from Hannah, now the program pulls the prompts (and other context) from the folder instead of being embedded into itself.

Boosted the timeout limit to (hopefully) prevent the script from failing due to time, if it still runs out then change the timeout limit within in the "plan" section (line 531).

Changed the internals of the cycler, any new prompts can now be inserted into the "plan" section, as opposed to having to write out each call to the LLM.

The biggest thing is I have completely removed the step4 prompt from the cycler, the LLM does not do good with it and we ultimately do not need it. Instead we have a script that generates the html file as opposed to having AI do it.



1/29/2026: Added "DTCCycle" folder. To use the folder follow the instructions below:  

Download Ollama: https://ollama.com/  

After installing Ollama, go to your command terminal (Windows Key + R, type cmd, Enter) and paste the following command:  

ollama pull qwen2.5:7b  

Afterwards, download and open the "DTCCycle" folder and run the python file (DO NOT REMOVE FROM FOLDER)  .
From there, paste in the responses found in "PROMPT ANSWERS" when asked by the code.
