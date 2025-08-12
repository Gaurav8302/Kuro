import React from 'react';
import { DndProvider } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';
import { useDrag, useDrop } from 'react-dnd';

const ItemType = 'TEST_ITEM';

function DragItem() {
  const [{ isDragging }, drag] = useDrag(() => ({
    type: ItemType,
    item: { id: 'test' },
    collect: (monitor) => ({
      isDragging: monitor.isDragging(),
    }),
  }));

  return (
    <div
      ref={drag}
      style={{
        padding: '16px',
        margin: '8px',
        backgroundColor: isDragging ? '#ccc' : '#f0f0f0',
        cursor: 'move',
        border: '1px solid #000',
      }}
    >
      Drag me!
    </div>
  );
}

function DropZone() {
  const [{ isOver }, drop] = useDrop(() => ({
    accept: ItemType,
    drop: (item) => {
      console.log('Dropped:', item);
      alert('Drop successful!');
    },
    collect: (monitor) => ({
      isOver: monitor.isOver(),
    }),
  }));

  return (
    <div
      ref={drop}
      style={{
        width: '200px',
        height: '200px',
        backgroundColor: isOver ? '#90EE90' : '#FFB6C1',
        border: '2px dashed #000',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        margin: '16px',
      }}
    >
      Drop zone
    </div>
  );
}

export default function DragDropTest() {
  return (
    <DndProvider backend={HTML5Backend}>
      <div style={{ padding: '20px' }}>
        <h1>Drag and Drop Test</h1>
        <DragItem />
        <DropZone />
      </div>
    </DndProvider>
  );
}
