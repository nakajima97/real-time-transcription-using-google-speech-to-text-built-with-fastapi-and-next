import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Mic, MicOff, AudioWaveformIcon as Waveform } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"

type TranscriptionViewProps = {
  isListening: boolean
  currentRecognition?: string
  recognitionHistory: string[]
  onToggleListening: () => void
}

export const TranscriptionView = ({
  isListening,
  currentRecognition,
  recognitionHistory,
  onToggleListening
}: TranscriptionViewProps) => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 flex items-center justify-center p-4">
      <Card className="w-full max-w-2xl bg-gray-800 border-gray-700 shadow-xl">
        <CardContent className="p-6">
          <h1 className="text-3xl font-bold text-center mb-8 text-white">リアルタイム文字起こし</h1>
          <div className="flex justify-center mb-8">
            <Button
              onClick={(e) => {
                console.log('Button clicked');
                onToggleListening();
              }}
              className={`${
                isListening ? "bg-red-500 hover:bg-red-600" : "bg-blue-500 hover:bg-blue-600"
              } text-white font-bold py-3 px-6 rounded-full transition-all duration-300 ease-in-out transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500`}
              aria-label={isListening ? "録音を停止" : "録音を開始"}
            >
              {isListening ? <MicOff className="mr-2" /> : <Mic className="mr-2" />}
              {isListening ? "録音を停止" : "録音を開始"}
            </Button>
          </div>
          <AnimatePresence>
            {isListening && (
              <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="flex justify-center mb-6"
              >
                <Waveform className="text-blue-400 animate-pulse" size={32} />
              </motion.div>
            )}
          </AnimatePresence>
          <motion.div
            className="bg-gray-700 p-6 rounded-lg min-h-[200px] max-h-[400px] overflow-y-auto text-white space-y-4"
            aria-live="polite"
            aria-atomic="true"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5 }}
          >
            {recognitionHistory.length > 0 ? (
              [...recognitionHistory].reverse().map((text, index) => (
                <p key={index}>{text}</p>
              ))
            ) : (
              !currentRecognition && (
                <p className="text-gray-400">録音を開始すると、ここに文字起こしが表示されます。</p>
              )
            )}
            {isListening && currentRecognition && (
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-blue-400"
              >
                {currentRecognition}
              </motion.p>
            )}
          </motion.div>
        </CardContent>
      </Card>
    </div>
  )
}