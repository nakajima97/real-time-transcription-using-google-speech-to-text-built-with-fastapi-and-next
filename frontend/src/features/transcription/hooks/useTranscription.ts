import { useState, useEffect, useCallback } from "react"

export const useTranscription = () => {
  const [isListening, setIsListening] = useState(false)
  const [transcript, setTranscript] = useState("")
  const [recognition, setRecognition] = useState<SpeechRecognition | null>(null)

  const toggleListening = useCallback(() => {
  }, [])

  return {
    isListening,
    transcript,
    toggleListening
  }
}
