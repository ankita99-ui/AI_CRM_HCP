import { Navigate, Route, Routes } from 'react-router-dom';
import { LogInteractionPage } from './pages/LogInteractionPage';

function App() {
  return (
    <Routes>
      <Route path="/" element={<LogInteractionPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
