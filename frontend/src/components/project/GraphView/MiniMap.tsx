import { useEffect, useRef } from "react";
import type cytoscape from "cytoscape";

interface Props { cy: cytoscape.Core | null; }

export default function MiniMap({ cy }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!cy || !canvasRef.current) return;

    const draw = () => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      const W = canvas.width;
      const H = canvas.height;
      ctx.clearRect(0, 0, W, H);
      ctx.fillStyle = "#0d1117";
      ctx.fillRect(0, 0, W, H);
      const extent = cy.extent();
      const scaleX = W / (extent.x2 - extent.x1 || 1);
      const scaleY = H / (extent.y2 - extent.y1 || 1);
      const scale = Math.min(scaleX, scaleY) * 0.9;
      const offsetX = (W - (extent.x2 - extent.x1) * scale) / 2;
      const offsetY = (H - (extent.y2 - extent.y1) * scale) / 2;
      cy.nodes().forEach((n) => {
        const pos = n.position();
        const x = (pos.x - extent.x1) * scale + offsetX;
        const y = (pos.y - extent.y1) * scale + offsetY;
        ctx.beginPath();
        ctx.arc(x, y, 2, 0, Math.PI * 2);
        ctx.fillStyle = n.style("background-color") as string;
        ctx.fill();
      });
    };

    cy.on("render", draw);
    draw();
    return () => { cy.off("render", draw); };
  }, [cy]);

  return (
    <canvas ref={canvasRef} width={160} height={100}
      className="absolute bottom-4 left-4 rounded border border-surface-border opacity-80 bg-surface" />
  );
}
