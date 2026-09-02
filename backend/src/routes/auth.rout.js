import {Router} from 'express'
import  {validate}  from '../middlewares/validator.midddleware.js'
import { verifyJWT } from '../middlewares/auth.middleware.js'
import { registerUser, login, logout, verifyEmail } from '../controllers/auth.controller.js'

const router = Router()

//Unsecurdes Routes
router.route("/register").post(validate,registerUser)
router.route("/login").post(login);
router.route("/verify-email/:verificationToken").get(verifyEmail);

//Secured Routes
router.route("/logout").post(verifyJWT, logout);

export default router;