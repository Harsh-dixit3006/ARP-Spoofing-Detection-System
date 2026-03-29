import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import api from '../services/api';
import { Lock, Mail, ShieldAlert } from 'lucide-react';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
        const { data } = await api.post('/auth/login', { email, password });
        localStorage.setItem('token', data.token);
        localStorage.setItem('user', JSON.stringify(data));
        navigate('/');
    } catch (err) {
        setError(err.response?.data?.message || 'Login failed');
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-center items-center py-12 px-4 sm:px-6 lg:px-8 font-sans">
      <div className="max-w-md w-full relative">
         <div className="absolute inset-0 bg-blue-500 blur-2xl opacity-10 rounded-full animate-pulse"></div>
         
         <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 relative z-10 shadow-2xl">
           <div className="text-center mb-8">
             <div className="mx-auto w-16 h-16 bg-blue-500/10 border border-blue-500/30 rounded-full flex items-center justify-center mb-4 shadow-[0_0_15px_rgba(59,130,246,0.3)]">
               <ShieldAlert className="w-8 h-8 text-blue-400" />
             </div>
             <h2 className="text-3xl font-extrabold text-slate-100 tracking-tight uppercase">SOC Access</h2>
             <p className="mt-2 text-sm text-slate-400">Sign in to monitor network anomalies</p>
           </div>
           
           {error && (
               <div className="mb-4 p-3 rounded bg-red-500/10 border border-red-500/50 text-red-500 text-sm text-center">
                   {error}
               </div>
           )}

           <form className="space-y-6" onSubmit={handleLogin}>
               <div className="relative">
                 <Mail className="w-5 h-5 text-slate-500 absolute left-3 top-3.5" />
                 <input 
                   type="email" 
                   required 
                   className="appearance-none rounded-xl relative block w-full pl-10 px-3 py-3 border border-slate-700 bg-slate-950 placeholder-slate-500 text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 sm:text-sm transition-colors" 
                   placeholder="Agent Email Address" 
                   value={email}
                   onChange={(e) => setEmail(e.target.value)}
                 />
               </div>
               <div className="relative">
                 <Lock className="w-5 h-5 text-slate-500 absolute left-3 top-3.5" />
                 <input 
                   type="password" 
                   required 
                   className="appearance-none rounded-xl relative block w-full pl-10 px-3 py-3 border border-slate-700 bg-slate-950 placeholder-slate-500 text-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 sm:text-sm transition-colors" 
                   placeholder="Passcode" 
                   value={password}
                   onChange={(e) => setPassword(e.target.value)}
                 />
               </div>

               <div>
                 <button type="submit" className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-bold rounded-xl text-white bg-blue-600 hover:bg-blue-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 focus:ring-offset-slate-900 transition-all uppercase tracking-widest shadow-[0_0_15px_rgba(37,99,235,0.4)]">
                   Authenticate
                 </button>
               </div>
           </form>

           <div className="mt-6 text-center text-sm">
             <span className="text-slate-500">No clearance? </span>
             <Link to="/signup" className="font-bold text-blue-400 hover:text-blue-300 ml-1 transition-colors">Request Access.</Link>
           </div>
         </div>
      </div>
    </div>
  );
};

export default Login;
