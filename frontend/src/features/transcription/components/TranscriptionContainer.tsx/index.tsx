"use client"

import { useTranscription } from "../../hooks/useTranscription"
import { TranscriptionView } from "../TranscriptionView"

export const TranscriptionContainer = () => {
  const { isListening, handleToggleListening, currentRecognition, recognitionHistory } = useTranscription()

  return (
    <TranscriptionView
      isListening={isListening}
      currentRecognition={currentRecognition}
      recognitionHistory={recognitionHistory}
      onToggleListening={handleToggleListening}
    />
  )
}