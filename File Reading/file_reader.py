#Import .pdf, .txt, or .md files. Output is the text we can input into ollama

#   download PyPDF2 and markdown
#   open command window
#   pip install PyPDF2
#   pip install markdown

import os
from PyPDF2 import PdfReader
import markdown

#Function to read md file and convert to html
def readfile(file_path):

    #Validate file existance
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"The file {file_path} was not found.")

    #Handle file extensions
    ext = os.path.splitext(file_path)[1].lower()

    print(f"---Reading {ext} file ---")## edit out
    

    #Handle PDF files
    if ext == '.pdf':
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text_content.append(page.extract_text() or "")
        return "\n".join(text_content)
            
    #Handle txt files
    elif ext == '.txt':
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    #Handle md files
    elif ext == '.md':
        with open(file_path, 'r', encoding='utf-8')as f:
            md_content = f.read()
            # to return raw text use , 'retun md_content'
            # to see the html version, use markdown.markdown(md_content)
            return md_content
    else:
        return f"Unsupported file extension: {ext}"



if __name__ == "__main__":
    path = input("Enter the file path (.pdf, .txt, .md): ").strip()
    try:
        content = readfile(path)
        print("\n--- EXTRACTED CONTENT ---")
        print(content[:500] + "...") # Printing first 500 chars to keep it clean
        
        # Optional: Save output to a standard text file
        save_choice = input("\nSave output to 'output.txt'? (y/n): ")
        if save_choice.lower() == 'y':
            with open("output.txt", "w", encoding="utf-8") as out:
                out.write(content)
            print("Saved to output.txt")
            
    except Exception as e:
        print(f"Error: {e}")
    

