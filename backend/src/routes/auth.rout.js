import {Router} from 'express'
import  {validate}  from '../middlewares/validator.midddleware.js'
import { verifyJWT } from '../middlewares/auth.middleware.js'
import { rateLimitDeveloperAccess } from '../middlewares/rate-limit.middleware.js'
import { registerUser, login, logout, verifyEmail, getCurrentUser, developerAccess } from '../controllers/auth.controller.js'

const router = Router()

//Unsecurdes Routes
router.route("/register").post(validate,registerUser)
router.route("/login").post(login);
router.route("/verify-email/:verificationToken").get(verifyEmail);

// Developer Access (rate-limited)
router.route("/developer-access").post(rateLimitDeveloperAccess, developerAccess);

//Secured Routes
router.route("/logout").post(verifyJWT, logout);
router.route("/me").get(verifyJWT, getCurrentUser);

export default router;