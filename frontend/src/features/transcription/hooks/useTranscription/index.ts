import { useEffect, useRef, useState } from 'react';
import { type Socket, io } from 'socket.io-client';
import { getMediaStream } from '../../utils/getMediaStream';

type WordRecognized = {
  isFinal: boolean;
  text: string;
};

export const useTranscription = () => {
  const [connection, setConnection] = useState<Socket>();
  const [currentRecognition, setCurrentRecognition] = useState<string>();
  const [recognitionHistory, setRecognitionHistory] = useState<string[]>([]);
  const [isListening, setIsListening] = useState<boolean>(false);
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioInputRef = useRef<AudioNode | null>(null);
  const processorRef = useRef<AudioWorkletNode | null>(null);

  const speechRecognized = (data: WordRecognized) => {
    if (data.isFinal) {
      setCurrentRecognition('...');
      setRecognitionHistory((old) => [data.text, ...old]);
    } else setCurrentRecognition(`${data.text}...`);
  };

  const connect = () => {
    connection?.disconnect();
    const socket = io(
      process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    );
    socket.on('connect', () => {
      setConnection(socket);
    });

    // Start recording
    socket.emit('start_google_cloud_stream');

    socket.on('receive_audio_text', (data: WordRecognized) => {
      speechRecognized(data);
    });
  };

  const disconnect = () => {
    if (!connection) return;
    connection?.emit('stop_google_cloud_stream');
    connection?.disconnect();
    processorRef.current?.disconnect();
    audioInputRef.current?.disconnect();
    audioContextRef.current?.close();
    setConnection(undefined);
    setIsListening(false);
  };

  useEffect(() => {
    (async () => {
      // サーバーとの接続があるか確認
      if (connection) {
        // 既に録音中であれば何もしない
        if (isListening) {
          return;
        }

        // マイクから音声を取得
        const stream = await getMediaStream();

        // オーディオコンテキストを作成
        audioContextRef.current = new window.AudioContext();

        // カスタムオーディオ処理を追加
        await audioContextRef.current.audioWorklet.addModule(
          '/src/worklets/recorderWorkletProcessor.js',
        );

        // オーディオコンテキストを再開
        audioContextRef.current.resume();

        // マイクからの音声入力を作成
        audioInputRef.current =
          audioContextRef.current.createMediaStreamSource(stream);

        // カスタムオーディオ処理を行うノードを作成
        processorRef.current = new AudioWorkletNode(
          audioContextRef.current,
          'recorder.worklet',
        );

        // オーディオノードを接続
        processorRef.current.connect(audioContextRef.current.destination);
        audioContextRef.current.resume();

        // マイクからの音声入力をオーディオノードに接続
        audioInputRef.current.connect(processorRef.current);

        // オーディオノードからのメッセージを受け取り、サーバーに音声データを送信
        processorRef.current.port.onmessage = (event: MessageEvent) => {
          const audioData = event.data;
          connection.emit('send_audio_data', { audio: audioData });
        };

        // 録音中の状態を更新
        setIsListening(true);
      }
    })();

    // クリーンアップ関数
    return () => {
      if (isListening) {
        processorRef.current?.disconnect();
        audioInputRef.current?.disconnect();
        if (audioContextRef.current?.state !== 'closed') {
          audioContextRef.current?.close();
        }
      }
    };
  }, [connection, isListening]);

  const handleToggleListening = () => {
    if (isListening) {
      console.log('Disconnecting...');
      disconnect();
    } else {
      console.log('Connecting...');
      connect();
    }
  };

  return {
    isListening,
    handleToggleListening,
    currentRecognition,
    recognitionHistory,
  };
};
