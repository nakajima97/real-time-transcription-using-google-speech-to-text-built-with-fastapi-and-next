"use client"

import { useTranscription } from "../../hooks/useTranscription"
import { TranscriptionView } from "../presentation/TranscriptionView"

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
