const sampleRate = 44100;

/**
 * MediaStreamオブジェクトを返す関数
 * @returns {Promise<MediaStream>} - MediaStreamオブジェクトを返すプロミス
 */
export const getMediaStream = async () => {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        sampleRate: sampleRate,
      },
    });
    return stream;
  } catch (error) {
    console.error('Error accessing microphone:', error);
    throw error;
  }
};