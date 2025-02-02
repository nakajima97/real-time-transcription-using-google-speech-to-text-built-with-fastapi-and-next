"use client"

import { useTranscription } from "../../hooks/useTranscription"
import { TranscriptionView } from "../TranscriptionView"

export const TranscriptionContainer = () => {
  const { isListening, transcript, toggleListening } = useTranscription()

  return (
    <TranscriptionView
      isListening={isListening}
      transcript={transcript}
      onToggleListening={toggleListening}
    />
  )
}