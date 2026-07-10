import logging

from fastapi import Depends
from firebase_admin import auth

from app.core.exceptions import BusinessException, ConflictException, ForbiddenException, NotFoundException
from app.models.address import Address
from app.models.patient import Patient
from app.models.user import User
from app.models.enums import UserRole
from app.repositories.user_repository import UserRepository, get_user_repository
from app.repositories.staff_repository import StaffRepository, get_staff_repository
from app.repositories.doctor_repository import DoctorRepository, get_doctor_repository
from app.repositories.patient_repository import PatientRepository, get_patient_repository
from app.schemas.user_schema import PatientRegisterRequest, UserCreate

logger = logging.getLogger(__name__)

class UserService():
    def __init__(
        self,
        repo: UserRepository,
        staff_repo: StaffRepository,
        doctor_repo: DoctorRepository,
        patient_repo: PatientRepository,
    ):
        self.repo = repo
        self.staff_repo = staff_repo
        self.doctor_repo = doctor_repo
        self.patient_repo = patient_repo
        
    
    async def assert_unique_email(self, email: str):
        if await self.repo.get_by_email(email):
            logger.warning("Conflict: Email '%s' already registered", email)
            raise ConflictException("Email already exists.")
        
    async def get_by_firebase_uid(self, firebase_uid: str) -> User | None:
        return await self.repo.get_by_firebase_uid(firebase_uid)
    
    async def register_patient(self, data: PatientRegisterRequest) -> User:
        await self.assert_unique_email(data.email)

        try:
            firebase_user = auth.create_user(email=data.email, password=data.password)
        
        except auth.EmailAlreadyExistsError:
            raise ConflictException("Email already exists in Firebase")
        
        user = await self.repo.save(
            User(
                firebase_uid=firebase_user.uid,
                email=data.email,
                role=UserRole.USER_PATIENT
            )
        )

        try:
            patient = await self.patient_repo.get_by_cpf(data.cpf)

            if not patient:
                patient = await self.patient_repo.save(
                    Patient(
                        name=data.name, 
                        email=data.email, 
                        cpf=data.cpf,
                        birth_date=data.birth_date, 
                        phone=data.phone,
                        address=Address(**data.address.model_dump()) if data.address else None,
                    )
                )

            user.patient_id = patient.id
            user = await self.repo.save(user)

            if patient.email != data.email:
                patient.email = data.email
                await self.patient_repo.save(patient)
            
        except Exception:
            logger.warning("Failed to create/link Patient during self-registration, reverting User id=%s", user.id)
            await self.repo.delete(user)

            try:
                auth.delete_user(firebase_user.uid)

            except Exception:
                logger.error("Failed to delete orphaned Firebase account uid=%s", firebase_user.uid, exc_info=True)
            raise

        logger.info("Patient self registered user_id=%s patient_id=%s", user.id, user.patient_id)
        return user


    async def create_user(self, creator: User, data: UserCreate) -> User:
        if data.role == UserRole.ADMIN and creator.role != UserRole.ADMIN:
            logger.warning("Forbidden: %s tried to create ADMIN", creator.id)
            raise ForbiddenException("Only ADMIN can create another ADMIN.")
        
        if data.role in (UserRole.ADMIN, UserRole.USER_ADMIN):
            if not data.staff_id:
                raise BusinessException(f"{data.role.value} requires staff_id.")
            if data.doctor_id or data.patient_id:
                raise BusinessException(f"{data.role.value} must not be linked to a doctor or patient.")
            if not await self.staff_repo.get_by_id(data.staff_id):
                raise NotFoundException("Staff not found.")
            
        elif data.role == UserRole.USER_DOCTOR:
            if not data.doctor_id:
                raise BusinessException("USER_DOCTOR requires doctor_id.")
            if data.staff_id or data.patient_id:
                raise BusinessException("USER_DOCTOR must not be linked to staff or patient.")
            if not await self.doctor_repo.get_by_id(data.doctor_id):
                raise NotFoundException("Doctor not found.")
            
        elif data.role == UserRole.USER_PATIENT:
            if not data.patient_id:
                raise BusinessException("USER_PATIENT requires patient_id.")
            if data.staff_id or data.doctor_id:
                raise BusinessException("USER_PATIENT must not be linked to staff or doctor.")
            if not await self.patient_repo.get_by_id(data.patient_id):
                raise NotFoundException("Patient not found.")

        await self.assert_unique_email(data.email)

        try:
            firebase_user = auth.create_user(email=data.email, password=data.password)
        except auth.EmailAlreadyExistsError:
            raise ConflictException("Email already registered in Firebase.")
        
        user = User(
            firebase_uid=firebase_user.uid,
            email=data.email,
            role=data.role,
            staff_id=data.staff_id,
            doctor_id=data.doctor_id,
            patient_id=data.patient_id,
        )

        try:
            saved = await self.repo.save(user)

        except Exception:
            logger.warning("Failed to save User locally, reverting Firebase account uid=%s", firebase_user.uid)
            try:
                auth.delete_user(firebase_user.uid)
            except Exception:
                logger.error("Failed to delete orphaned Firebase account uid=%s", firebase_user.uid, exc_info=True)
            raise

        logger.info("User created id=%s role=%s by=%s", saved.id, saved.role, creator.id)
        return saved
    
def get_user_service(
    repo: UserRepository = Depends(get_user_repository),
    staff_repo: StaffRepository = Depends(get_staff_repository),
    doctor_repo: DoctorRepository = Depends(get_doctor_repository),
    patient_repo: PatientRepository = Depends(get_patient_repository),
) -> UserService:
    return UserService(
        repo=repo, 
        staff_repo=staff_repo, 
        doctor_repo=doctor_repo, 
        patient_repo=patient_repo
    )
