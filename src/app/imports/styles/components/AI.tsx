import React, { useEffect, useRef, useState } from "react";
import * as tmImage from "@teachablemachine/image";

const URL = "https://teachablemachine.withgoogle.com/models/dt-an-AbF/";

export default function AI() {
  const webcamRef = useRef<any>(null);

  const [model, setModel] = useState<any>(null);
  const [prediction, setPrediction] = useState<string>("Loading...");
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    loadModel();
  }, []);

  async function loadModel() {
    try {
      const modelURL = URL + "model.json";
      const metadataURL = URL + "metadata.json";

      const loadedModel = await tmImage.load(modelURL, metadataURL);

      setModel(loadedModel);

      const webcam = new tmImage.Webcam(300, 300, true);

      await webcam.setup();
      await webcam.play();

      webcamRef.current = webcam;

      document
        .getElementById("webcam-container")
        ?.appendChild(webcam.canvas);

      setLoading(false);

      window.requestAnimationFrame(loop);
    } catch (error) {
      console.error(error);
    }
  }

  async function loop() {
    if (webcamRef.current) {
      webcamRef.current.update();

      await predict();

      window.requestAnimationFrame(loop);
    }
  }

  async function predict() {
    if (!model || !webcamRef.current) return;

    const predictions = await model.predict(webcamRef.current.canvas);

    let highestPrediction = predictions[0];

    predictions.forEach((p: any) => {
      if (p.probability > highestPrediction.probability) {
        highestPrediction = p;
      }
    });

    setPrediction(
      `${highestPrediction.className} (${(
        highestPrediction.probability * 100
      ).toFixed(2)}%)`
    );

    await fetch("http://127.0.0.1:5000/api/ai/predict", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        prediction: highestPrediction.className,
        confidence: (
          highestPrediction.probability * 100
        ).toFixed(2),
      }),
    });
  }

  return (
    <div className="bg-white p-6 rounded-xl shadow-md">
      <h1 className="text-2xl font-bold text-green-600 mb-4">
        AI Detection System
      </h1>

      {loading && <p>Loading AI Model...</p>}

      <div id="webcam-container"></div>

      <h2 className="mt-4 text-lg font-semibold">
        {prediction}
      </h2>
    </div>
  );
}