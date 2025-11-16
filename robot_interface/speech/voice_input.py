import speech_recognition as sr

def listen_command():
    r = sr.Recognizer()
    mic = sr.Microphone()
    with mic as source:
        print("Listening for your command...")
        r.adjust_for_ambient_noise(source)
        audio = r.listen(source)
    try:
        command = r.recognize_google(audio)
        print("You said:", command)
        return command
    except sr.UnknownValueError:
        print("Sorry, could not understand audio")
        return ""
    except sr.RequestError:
        print("Could not request results from Google speech Recognition service")
        return ""
