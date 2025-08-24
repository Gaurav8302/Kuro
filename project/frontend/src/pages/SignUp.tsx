import { useState } from 'react';
import { motion } from 'framer-motion';
import { useNavigate, Link } from 'react-router-dom';
import { useSignUp, useSignIn } from '@clerk/clerk-react';
import { 
  Mail, 
  Lock, 
  Eye, 
  EyeOff, 
  ArrowLeft,
  AlertCircle,
  User,
  Zap
} from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { HolographicButton } from '@/components/HolographicButton';
import { HolographicCard } from '@/components/HolographicCard';
import { HolographicBackground } from '@/components/HolographicBackground';
import { HoloSparklesIcon } from '@/components/HolographicIcons';

const SignUp = () => {
  const navigate = useNavigate();
  const { signUp, setActive, isLoaded: signUpLoaded } = useSignUp();
  const { signIn } = useSignIn();
  
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    email: '',
    password: ''
  });
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [pendingVerification, setPendingVerification] = useState(false);
  const [code, setCode] = useState('');

  // Show loading if Clerk is not ready
  if (!signUpLoaded) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center relative overflow-hidden">
        <HolographicBackground variant="subtle" />
        <div className="text-center">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
            className="w-16 h-16 mx-auto mb-6"
          >
            <div className="w-full h-full rounded-full border-4 border-holo-cyan-400/30 border-t-holo-cyan-400 shadow-holo-glow" />
          </motion.div>
          <p className="text-holo-cyan-400 font-orbitron tracking-wide">LOADING REGISTRATION...</p>
        </div>
      </div>
    );
  }

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleGoogleSignUp = async () => {
    if (!signUpLoaded || !signIn) return;

    setIsLoading(true);
    setError('');

    try {
      await signIn.authenticateWithRedirect({
        strategy: 'oauth_google',
        redirectUrl: `${window.location.origin}/sso-callback`,
        redirectUrlComplete: `${window.location.origin}/chat`,
      });
    } catch (err: any) {
      console.error('Google sign up error:', err);
      setError(err.errors?.[0]?.message || 'Failed to sign up with Google. Please try again.');
      setIsLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!signUpLoaded || !signUp) return;

    setIsLoading(true);
    setError('');

    try {
      await signUp.create({
        firstName: formData.firstName,
        lastName: formData.lastName,
        emailAddress: formData.email,
        password: formData.password,
      });

      await signUp.prepareEmailAddressVerification({ strategy: 'email_code' });
      setPendingVerification(true);
    } catch (err: any) {
      console.error('Sign up error:', err);
      setError(err.errors?.[0]?.message || 'Failed to sign up. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const onPressVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!signUpLoaded || !signUp) return;

    setIsLoading(true);
    setError('');

    try {
      if (!signUp.createdSessionId) {
        throw new Error('No session created during sign up');
      }

      const completeSignUp = await signUp.attemptEmailAddressVerification({
        code,
      });

      if (completeSignUp.status !== 'complete') {
        console.error('Sign up not complete:', completeSignUp);
        throw new Error('Verification failed');
      }

      if (completeSignUp.createdSessionId) {
        await setActive({ session: completeSignUp.createdSessionId });
        navigate('/chat');
      } else {
        throw new Error('No session created after verification');
      }
    } catch (err: any) {
      console.error('Verification error:', err);
      setError(err.errors?.[0]?.message || 'Failed to verify. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const isFormValid = formData.firstName && formData.lastName && formData.email && formData.password;

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4 relative overflow-hidden">
      <HolographicBackground variant="default" />

      <div className="relative z-10 w-full max-w-md">
        {/* Back button */}
        <motion.div
          initial={{ opacity: 0, x: -30, filter: 'blur(5px)' }}
          animate={{ opacity: 1, x: 0, filter: 'blur(0px)' }}
          transition={{ duration: 0.5 }}
          className="mb-6"
        >
          <HolographicButton
            variant="ghost"
            size="md"
            onClick={() => navigate('/')}
            className="font-orbitron tracking-wide"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            RETURN TO BASE
          </HolographicButton>
        </motion.div>

        {/* Sign Up Card */}
        <motion.div
          initial={{ opacity: 0, y: 30, scale: 0.8, filter: 'blur(10px)' }}
          animate={{ opacity: 1, y: 0, scale: 1, filter: 'blur(0px)' }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        >
          <HolographicCard variant="intense" className="overflow-hidden">
            <div className="text-center p-8 pb-6 relative">
              {/* Header scan line */}
              <motion.div
                className="absolute top-0 left-0 w-full h-0.5 bg-gradient-to-r from-transparent via-holo-cyan-400 to-transparent"
                animate={{ opacity: [0.3, 0.8, 0.3] }}
                transition={{ duration: 2, repeat: Infinity }}
              />
              
              <div className="flex justify-center mb-4">
                <motion.div 
                  className="w-20 h-20 glass-panel border-holo-cyan-400/50 rounded-full flex items-center justify-center overflow-hidden shadow-holo-glow"
                  animate={{ 
                    scale: [1, 1.1, 1],
                    rotate: [0, 5, -5, 0]
                  }}
                  transition={{ duration: 4, repeat: Infinity }}
                >
                  <img src="/kuroai.png" alt="Kuro AI" className="w-full h-full object-cover rounded-full" />
                </motion.div>
              </div>
              <h2 className="text-3xl font-bold text-holo-cyan-300 mb-3 font-orbitron tracking-wide text-holo-glow">
                NEURAL REGISTRATION
              </h2>
              <p className="text-holo-cyan-100/70 text-sm font-space">
                Initialize your neural profile and begin AI interface training
              </p>
            </div>

            <div className="space-y-6 p-8 pt-0">
              {error && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.3 }}
                >
                  <Alert className="bg-holo-magenta-500/10 border-holo-magenta-400/30 glass-panel">
                  <AlertCircle className="h-4 w-4 text-holo-magenta-400" />
                  <AlertDescription className="text-holo-magenta-200 font-space">
                    {error}
                  </AlertDescription>
                </Alert>
                </motion.div>
              )}

              {!pendingVerification ? (
                <form onSubmit={handleSubmit} className="space-y-4">
                  {/* Google Sign Up Button */}
                  <HolographicButton
                    variant="ghost"
                    size="lg"
                    className="w-full font-orbitron tracking-wide"
                    onClick={handleGoogleSignUp}
                    disabled={isLoading}
                  >
                    <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
                      <path fill="#00e6d6" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                      <path fill="#1a8cff" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                      <path fill="#8c1aff" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                      <path fill="#ff1ab1" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                    </svg>
                    GOOGLE REGISTRATION
                  </HolographicButton>

                  {/* Divider */}
                  <div className="relative my-6">
                    <div className="absolute inset-0 flex items-center">
                      <div className="w-full border-t border-holo-cyan-500/30"></div>
                    </div>
                    <div className="relative flex justify-center text-sm">
                      <span className="glass-panel px-6 py-2 text-holo-cyan-400/70 font-orbitron tracking-wide">OR MANUAL REGISTRATION</span>
                    </div>
                  </div>

                  {/* Name Fields */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-2">
                      <label className="text-sm font-medium text-holo-cyan-300 font-orbitron tracking-wide">
                        FIRST ID
                      </label>
                      <div className="relative">
                        <User className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-holo-cyan-400/60" />
                        <Input
                          type="text"
                          value={formData.firstName}
                          onChange={(e) => handleInputChange('firstName', e.target.value)}
                          placeholder="Neural"
                          className="pl-10 glass-panel border-holo-cyan-400/30 text-holo-cyan-100 placeholder:text-holo-cyan-400/40 focus:border-holo-cyan-400 focus:shadow-holo-glow font-space"
                          required
                        />
                      </div>
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium text-holo-cyan-300 font-orbitron tracking-wide">
                        LAST ID
                      </label>
                      <Input
                        type="text"
                        value={formData.lastName}
                        onChange={(e) => handleInputChange('lastName', e.target.value)}
                        placeholder="Operator"
                        className="glass-panel border-holo-cyan-400/30 text-holo-cyan-100 placeholder:text-holo-cyan-400/40 focus:border-holo-cyan-400 focus:shadow-holo-glow font-space"
                        required
                      />
                    </div>
                  </div>

                  {/* Email */}
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-holo-cyan-300 font-orbitron tracking-wide">
                      EMAIL IDENTIFIER
                    </label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-holo-cyan-400/60" />
                      <Input
                        type="email"
                        value={formData.email}
                        onChange={(e) => handleInputChange('email', e.target.value)}
                        placeholder="neural.interface@domain.net"
                        className="pl-10 glass-panel border-holo-cyan-400/30 text-holo-cyan-100 placeholder:text-holo-cyan-400/40 focus:border-holo-cyan-400 focus:shadow-holo-glow font-space"
                        required
                      />
                    </div>
                  </div>

                  {/* Password */}
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-holo-cyan-300 font-orbitron tracking-wide">
                      ACCESS CODE
                    </label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-holo-cyan-400/60" />
                      <Input
                        type={showPassword ? 'text' : 'password'}
                        value={formData.password}
                        onChange={(e) => handleInputChange('password', e.target.value)}
                        placeholder="Create neural access code"
                        className="pl-10 pr-10 glass-panel border-holo-cyan-400/30 text-holo-cyan-100 placeholder:text-holo-cyan-400/40 focus:border-holo-cyan-400 focus:shadow-holo-glow font-orbitron"
                        required
                      />
                      <motion.button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-3 top-1/2 transform -translate-y-1/2 text-holo-cyan-400/60 hover:text-holo-cyan-400 transition-colors duration-300"
                        whileHover={{ scale: 1.1 }}
                        whileTap={{ scale: 0.9 }}
                      >
                        {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </motion.button>
                    </div>
                  </div>

                  {/* Sign Up Button */}
                  <HolographicButton
                    variant="primary"
                    size="lg"
                    className="w-full font-orbitron tracking-wide"
                    disabled={isLoading || !isFormValid}
                    onClick={handleSubmit}
                  >
                    {isLoading ? (
                      <>
                        <motion.div
                          animate={{ rotate: 360 }}
                          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                          className="mr-2"
                        >
                          <Zap className="w-4 h-4" />
                        </motion.div>
                        CREATING PROFILE...
                      </>
                    ) : (
                      <>
                        <HoloSparklesIcon size={16} className="mr-2" />
                        CREATE NEURAL PROFILE
                      </>
                    )}
                  </HolographicButton>
                </form>
              ) : (
                <form onSubmit={onPressVerify} className="space-y-6">
                  <div className="text-center space-y-2">
                    <h3 className="text-lg font-medium text-holo-cyan-300 font-orbitron tracking-wide">VERIFY NEURAL LINK</h3>
                    <p className="text-holo-cyan-100/70 text-sm font-space">
                      Verification code transmitted to {formData.email}
                    </p>
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium text-holo-cyan-300 font-orbitron tracking-wide">
                      VERIFICATION SEQUENCE
                    </label>
                    <Input
                      type="text"
                      value={code}
                      onChange={(e) => setCode(e.target.value)}
                      placeholder="Enter neural verification code"
                      className="glass-panel border-holo-cyan-400/30 text-holo-cyan-100 placeholder:text-holo-cyan-400/40 focus:border-holo-cyan-400 focus:shadow-holo-glow text-center font-orbitron tracking-wider"
                      required
                    />
                  </div>

                  <HolographicButton
                    variant="primary"
                    size="lg"
                    className="w-full font-orbitron tracking-wide"
                    disabled={isLoading || !code}
                    onClick={onPressVerify}
                  >
                    {isLoading ? (
                      <>
                        <motion.div
                          animate={{ rotate: 360 }}
                          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                          className="mr-2"
                        >
                          <Zap className="w-4 h-4" />
                        </motion.div>
                        VERIFYING...
                      </>
                    ) : (
                      <>
                        <HoloSparklesIcon size={16} className="mr-2" />
                        VERIFY NEURAL LINK
                      </>
                    )}
                  </HolographicButton>
                </form>
              )}

              {/* Sign In Link */}
              <div className="text-center pt-6 border-t border-holo-cyan-500/20">
                <p className="text-holo-cyan-100/70 text-sm font-space">
                  Already have an account?{' '}
                  <Link 
                    to="/auth/signin" 
                    className="text-holo-cyan-400 hover:text-holo-cyan-300 font-medium font-orbitron tracking-wide hover:text-holo-glow transition-all duration-300"
                  >
                    AUTHENTICATE HERE
                  </Link>
                </p>
              </div>
            </div>
          </HolographicCard>
        </motion.div>
      </div>
    </div>
  );
};

export default SignUp;